program test_newimpl_face_flux_hostmem
  use, intrinsic :: iso_c_binding, only: c_double, c_int, c_ptr, c_loc
  use milhoja_types_mod, only: MILHOJA_REAL
  use newimpl_face_flux_adapter_mod, only: newimpl_face_flux_adapter
  implicit none

  integer, parameter :: nxb = 16, nyb = 16, nguard = 3
  integer, parameter :: nxg = nxb + 2 * nguard
  integer, parameter :: nyg = nyb + 2 * nguard
  integer, parameter :: nstate = 8, nflux = 5
  real(MILHOJA_REAL), parameter :: tolerance = 1.0e-12_MILHOJA_REAL

  interface
    function newimpl_face_flux_hostmem_initialize_c() result(error) &
        bind(c, name="newimpl_face_flux_hostmem_initialize_c")
      import :: c_int
      integer(c_int) :: error
    end function

    function newimpl_face_flux_hostmem_finalize_c() result(error) &
        bind(c, name="newimpl_face_flux_hostmem_finalize_c")
      import :: c_int
      integer(c_int) :: error
    end function

    function run_newimpl_face_flux_hostmem_c( &
        state, flux_x, flux_y, ndim, density_floor, pressure_floor, &
        tiny_state, viscosity, weno_epsilon, flattening_eta, &
        flattening_flag, hybrid_flag, shock_marker_flag, max_speed, &
        status, failed_face) result(error) &
        bind(c, name="run_newimpl_face_flux_hostmem_c")
      import :: c_double, c_int, c_ptr
      type(c_ptr), value :: state, flux_x, flux_y
      integer(c_int), value :: ndim
      real(c_double), value :: density_floor, pressure_floor, tiny_state
      real(c_double), value :: viscosity, weno_epsilon, flattening_eta
      integer(c_int), value :: flattening_flag, hybrid_flag
      integer(c_int), value :: shock_marker_flag
      real(c_double), intent(out) :: max_speed
      integer(c_int), intent(out) :: status, failed_face(4)
      integer(c_int) :: error
    end function
  end interface

  integer(c_int) :: error

  error = newimpl_face_flux_hostmem_initialize_c()
#ifdef NEWIMPL_CUDA_OPENACC
  if (error /= 0) error stop "Unable to initialize Milhoja CUDA/OpenACC"
#else
  if (error /= 0) error stop "Unable to initialize Milhoja HOSTMEM"
#endif

  call run_case("constant 1D", 1, .false.)
  call run_case("constant 2D", 2, .false.)
  call run_case("failure diagnostics", 2, .true.)

  error = newimpl_face_flux_hostmem_finalize_c()
#ifdef NEWIMPL_CUDA_OPENACC
  if (error /= 0) error stop "Unable to finalize Milhoja CUDA/OpenACC"
#else
  if (error /= 0) error stop "Unable to finalize Milhoja HOSTMEM"
#endif
#ifdef NEWIMPL_CUDA_OPENACC
  print *, "NewImpl CUDA/OpenACC runtime comparisons passed"
#else
  print *, "NewImpl HOSTMEM runtime comparisons passed"
#endif

contains

  subroutine run_case(name, ndim, make_failure)
    character(len=*), intent(in) :: name
    integer, intent(in) :: ndim
    logical, intent(in) :: make_failure

    integer :: i, j, flattening_flag
    integer :: lo(3), hi(3), lbound(3)
    integer :: direct_status(1), direct_failed(4)
    integer(c_int) :: packet_status, packet_failed(4), run_error
    real(MILHOJA_REAL) :: direct_speed(1)
    real(c_double) :: packet_speed
    real(MILHOJA_REAL), allocatable, target :: packet_state(:, :, :, :)
    real(MILHOJA_REAL), allocatable, target :: direct_state(:, :, :, :)
    real(MILHOJA_REAL), allocatable, target :: direct_x(:, :, :, :)
    real(MILHOJA_REAL), allocatable, target :: direct_y(:, :, :, :)
    real(MILHOJA_REAL), allocatable, target :: packet_x(:, :, :, :)
    real(MILHOJA_REAL), allocatable, target :: packet_y(:, :, :, :)
    real(MILHOJA_REAL), allocatable :: flat(:, :, :, :)
    real(MILHOJA_REAL), allocatable :: minus(:, :, :, :)
    real(MILHOJA_REAL), allocatable :: plus(:, :, :, :)

    lo = [1, 1, 1]
    hi = [nxb, nyb, 1]
    lbound = [1 - nguard, 1 - nguard, 1]

#ifdef NEWIMPL_VARIABLE_FIRST
    allocate(direct_state(nstate, nxg, nyg, 1))
    allocate(direct_x(nflux, nxb + 1, nyb, 1))
    allocate(direct_y(nflux, nxb, nyb + 1, 1))
    allocate(flat(1, nxb + 2, nyb + 2, 1))
    allocate(minus(7, nxb + 2, nyb + 2, 1))
    allocate(plus(7, nxb + 2, nyb + 2, 1))
#else
    allocate(direct_state(nxg, nyg, 1, nstate))
    allocate(direct_x(nxb + 1, nyb, 1, nflux))
    allocate(direct_y(nxb, nyb + 1, 1, nflux))
    allocate(flat(nxb + 2, nyb + 2, 1, 1))
    allocate(minus(nxb + 2, nyb + 2, 1, 7))
    allocate(plus(nxb + 2, nyb + 2, 1, 7))
#endif
    allocate(packet_state(nxg, nyg, 1, nstate))
    allocate(packet_x(nxb + 1, nyb, 1, nflux))
    allocate(packet_y(nxb, nyb + 1, 1, nflux))

    do j = 1, nyg
      do i = 1, nxg
        packet_state(i, j, 1, :) = [ &
          2.0_MILHOJA_REAL, 0.4_MILHOJA_REAL, -0.3_MILHOJA_REAL, &
          0.2_MILHOJA_REAL, 1.0_MILHOJA_REAL, 1.4_MILHOJA_REAL, &
          2.5_MILHOJA_REAL, 0.0_MILHOJA_REAL]
#ifdef NEWIMPL_VARIABLE_FIRST
        direct_state(:, i, j, 1) = packet_state(i, j, 1, :)
#else
        direct_state(i, j, 1, :) = packet_state(i, j, 1, :)
#endif
      end do
    end do
    flattening_flag = 1
    if (make_failure) then
      packet_state(:, :, :, 6) = -1.0_MILHOJA_REAL
#ifdef NEWIMPL_VARIABLE_FIRST
      direct_state(6, :, :, :) = -1.0_MILHOJA_REAL
#else
      direct_state(:, :, :, 6) = -1.0_MILHOJA_REAL
#endif
      flattening_flag = 0
    end if

    direct_x = -huge(1.0_MILHOJA_REAL)
    direct_y = -huge(1.0_MILHOJA_REAL)
    ! Initialize independently. An assignment from a variable-first direct
    ! array would legally reallocate these allocatables to the wrong shape.
    packet_x = -huge(1.0_MILHOJA_REAL)
    packet_y = -huge(1.0_MILHOJA_REAL)
    call require(all(shape(packet_x) == [nxb + 1, nyb, 1, nflux]), &
      name // ": X packet shape")
    call require(all(shape(packet_y) == [nxb, nyb + 1, 1, nflux]), &
      name // ": Y packet shape")
    flat = 0.0_MILHOJA_REAL
    minus = 0.0_MILHOJA_REAL
    plus = 0.0_MILHOJA_REAL

    call newimpl_face_flux_adapter( &
      lo, hi, lbound, direct_state, direct_x, direct_y, flat, minus, plus, &
      1.0e-12_MILHOJA_REAL, 1.0e-12_MILHOJA_REAL, &
      1.0e-30_MILHOJA_REAL, 0.0_MILHOJA_REAL, &
      1.0e-36_MILHOJA_REAL, 1.0e-99_MILHOJA_REAL, &
      flattening_flag, 0, 0, ndim, direct_speed, direct_status, direct_failed)

    run_error = run_newimpl_face_flux_hostmem_c( &
      c_loc(packet_state), c_loc(packet_x), c_loc(packet_y), int(ndim, c_int), &
      1.0e-12_c_double, 1.0e-12_c_double, 1.0e-30_c_double, &
      0.0_c_double, 1.0e-36_c_double, 1.0e-99_c_double, &
      int(flattening_flag, c_int), 0_c_int, 0_c_int, packet_speed, &
      packet_status, packet_failed)
#ifdef NEWIMPL_CUDA_OPENACC
    if (run_error /= 0) error stop "CUDA/OpenACC packet execution failed"
#else
    if (run_error /= 0) error stop "HOSTMEM packet execution failed"
#endif

    call require(packet_status == direct_status(1), name // ": status")
    call require(all(packet_failed == direct_failed), name // ": failed face")
    call require(close(packet_speed, direct_speed(1)), name // ": max speed")

    if (.not. make_failure) then
#ifdef NEWIMPL_VARIABLE_FIRST
      call require(all_close_transposed(packet_x, direct_x), name // ": X flux")
      if (ndim == 2) then
        call require(all_close_transposed(packet_y, direct_y), name // ": Y flux")
      end if
#else
      call require(all_close(packet_x, direct_x), name // ": X flux")
      if (ndim == 2) then
        call require(all_close(packet_y, direct_y), name // ": Y flux")
      end if
#endif
    else
      call require(direct_status(1) /= 0, name // ": expected failure")
      call require(any(direct_failed /= 0), name // ": diagnostic populated")
    end if

    print *, trim(name), " passed"
  end subroutine

  logical function close(actual, expected)
    real(MILHOJA_REAL), intent(in) :: actual, expected
    close = abs(actual - expected) <= tolerance * &
      (1.0_MILHOJA_REAL + max(abs(actual), abs(expected)))
  end function

  logical function all_close(actual, expected)
    real(MILHOJA_REAL), intent(in) :: actual(:, :, :, :), expected(:, :, :, :)
    all_close = maxval(abs(actual - expected)) <= tolerance * &
      (1.0_MILHOJA_REAL + max(maxval(abs(actual)), maxval(abs(expected))))
  end function

  logical function all_close_transposed(actual, expected)
    real(MILHOJA_REAL), intent(in) :: actual(:, :, :, :), expected(:, :, :, :)
    integer :: i, j, k, variable
    real(MILHOJA_REAL) :: difference, scale

    if (size(actual, 1) /= size(expected, 2) .or. &
        size(actual, 2) /= size(expected, 3) .or. &
        size(actual, 3) /= size(expected, 4) .or. &
        size(actual, 4) /= size(expected, 1)) then
      all_close_transposed = .false.
      return
    end if

    difference = 0.0_MILHOJA_REAL
    scale = 0.0_MILHOJA_REAL
    do variable = 1, size(actual, 4)
      do k = 1, size(actual, 3)
        do j = 1, size(actual, 2)
          do i = 1, size(actual, 1)
            difference = max(difference, &
              abs(actual(i, j, k, variable) - expected(variable, i, j, k)))
            scale = max(scale, abs(actual(i, j, k, variable)), &
              abs(expected(variable, i, j, k)))
          end do
        end do
      end do
    end do
    all_close_transposed = difference <= tolerance * (1.0_MILHOJA_REAL + scale)
  end function

  subroutine require(condition, message)
    logical, intent(in) :: condition
    character(len=*), intent(in) :: message
    if (.not. condition) then
      print *, "FAILED: ", trim(message)
      error stop 1
    end if
  end subroutine

end program
