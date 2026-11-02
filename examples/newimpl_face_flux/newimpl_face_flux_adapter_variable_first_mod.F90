module newimpl_face_flux_adapter_mod
  use milhoja_types_mod, only: MILHOJA_REAL
  use newimpl_hydro, only: cell_field, flux_field, hydro_parameters, hydro_workspace, &
                           hy_getFaceFlux, HY_BAD_INPUT
  implicit none
  private
  public :: newimpl_face_flux_adapter

contains

  subroutine newimpl_face_flux_adapter( &
      tile_lo, tile_hi, tile_lbound, state, flux_x, flux_y, &
      flat, reconstructed_minus, reconstructed_plus, &
      density_floor, pressure_floor, tiny_state, viscosity, &
      weno_epsilon, flattening_eta, flattening_flag, hybrid_flag, &
      shock_marker_flag, ndim, max_speed, status, failed_face)
    integer, intent(in) :: tile_lo(:), tile_hi(:), tile_lbound(:)
    real(MILHOJA_REAL), target, contiguous, intent(in) :: state(:, :, :, :)
    real(MILHOJA_REAL), target, contiguous, intent(out) :: flux_x(:, :, :, :)
    real(MILHOJA_REAL), target, contiguous, intent(out) :: flux_y(:, :, :, :)
    real(MILHOJA_REAL), target, contiguous, intent(inout) :: flat(:, :, :, :)
    real(MILHOJA_REAL), target, contiguous, intent(inout) :: reconstructed_minus(:, :, :, :)
    real(MILHOJA_REAL), target, contiguous, intent(inout) :: reconstructed_plus(:, :, :, :)
    real(MILHOJA_REAL), intent(in) :: density_floor, pressure_floor, tiny_state, viscosity
    real(MILHOJA_REAL), intent(in) :: weno_epsilon, flattening_eta
    integer, intent(in) :: flattening_flag, hybrid_flag, shock_marker_flag, ndim
    real(MILHOJA_REAL), intent(out) :: max_speed(:)
    integer, intent(out) :: status(:), failed_face(:)

    integer :: available_hi(3), input_map(7), output_map(5)
    type(cell_field) :: state_view
    type(flux_field) :: flux_view
    type(hydro_parameters) :: parameters
    type(hydro_workspace) :: workspace

    if (ndim < 1 .or. ndim > 2) then
      max_speed = 0.0_MILHOJA_REAL
      status = HY_BAD_INPUT
      failed_face = 0
      return
    end if

    input_map = [1, 2, 3, 4, 5, 6, 7]
    output_map = [1, 2, 3, 4, 5]
    available_hi = tile_lbound + [size(state, 2), size(state, 3), size(state, 4)] - 1

    state_view%values( &
      1:size(state, 1), &
      tile_lbound(1):available_hi(1), &
      tile_lbound(2):available_hi(2), &
      tile_lbound(3):available_hi(3), 1:1) => state

    allocate(flux_view%directions(2))
    flux_view%directions(1)%values( &
      1:size(flux_x, 1), &
      tile_lo(1):tile_hi(1) + 1, &
      tile_lo(2):tile_hi(2), &
      tile_lo(3):tile_hi(3), 1:1) => flux_x
    flux_view%directions(2)%values( &
      1:size(flux_y, 1), &
      tile_lo(1):tile_hi(1), &
      tile_lo(2):tile_hi(2) + 1, &
      tile_lo(3):tile_hi(3), 1:1) => flux_y

    workspace%flat%values( &
      1:1, tile_lo(1) - 1:tile_hi(1) + 1, &
      tile_lo(2) - 1:tile_hi(2) + 1, &
      tile_lo(3):tile_hi(3), 1:1) => flat
    workspace%minus%values( &
      1:7, tile_lo(1) - 1:tile_hi(1) + 1, &
      tile_lo(2) - 1:tile_hi(2) + 1, &
      tile_lo(3):tile_hi(3), 1:1) => reconstructed_minus
    workspace%plus%values( &
      1:7, tile_lo(1) - 1:tile_hi(1) + 1, &
      tile_lo(2) - 1:tile_hi(2) + 1, &
      tile_lo(3):tile_hi(3), 1:1) => reconstructed_plus
    workspace%lo = [tile_lo(1) - 1, tile_lo(2) - 1, tile_lo(3)]
    workspace%hi = [tile_hi(1) + 1, tile_hi(2) + 1, tile_hi(3)]
    workspace%blocks = 1

    parameters%density_floor = density_floor
    parameters%pressure_floor = pressure_floor
    parameters%tiny_state = tiny_state
    parameters%viscosity = viscosity
    parameters%weno_epsilon = weno_epsilon
    parameters%flattening_eta = flattening_eta
    parameters%flattening = flattening_flag /= 0
    parameters%hybrid = hybrid_flag /= 0
    parameters%shock_marker_present = shock_marker_flag /= 0

    call hy_getFaceFlux( &
      state_view, flux_view, 1, tile_lo, tile_hi, tile_lbound, available_hi, &
      ndim, input_map, output_map, 8, parameters, workspace, max_speed(1), &
      status(1), failed_face(1:4))

    nullify(state_view%values)
    nullify(workspace%flat%values, workspace%minus%values, workspace%plus%values)
    nullify(flux_view%directions(1)%values, flux_view%directions(2)%values)
    deallocate(flux_view%directions)
  end subroutine newimpl_face_flux_adapter

end module newimpl_face_flux_adapter_mod
