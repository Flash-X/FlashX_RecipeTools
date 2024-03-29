module gpu_taskfn_0_mod
   implicit none
   private

   public :: gpu_taskfn_0_Fortran
   public :: gpu_taskfn_0_Cpp2C

   interface
      !> C++ task function that TimeAdvance passes to Orchestration unit
      subroutine gpu_taskfn_0_Cpp2C(C_tId, C_dataItemPtr) &
            bind(c, name="gpu_taskfn_0_Cpp2C")
         use iso_c_binding, ONLY : C_PTR
         use milhoja_types_mod, ONLY : MILHOJA_INT
         integer(MILHOJA_INT), intent(IN), value :: C_tId
         type(C_PTR), intent(IN), value :: C_dataItemPtr
      end subroutine gpu_taskfn_0_Cpp2C
   end interface

contains

   subroutine gpu_taskfn_0_Fortran( &
               C_packet_h, &
               dataQ_h, &
               nTiles_d, &
               external_Hydro_dt_d, &
               external_Hydro_dtOld_d, &
               external_Hydro_stage_d, &
               tile_arrayBounds_d, &
               tile_deltas_d, &
               tile_interior_d, &
               tile_lbound_d, &
               tile_lo_d, &
               CC_1_d, &
               scratch_Hydro_cvol_fake_d, &
               scratch_Hydro_fareaX_fake_d, &
               scratch_Hydro_fareaY_fake_d, &
               scratch_Hydro_fareaZ_fake_d, &
               scratch_Hydro_hy_Vc_d, &
               scratch_Hydro_hy_flat3d_d, &
               scratch_Hydro_hy_flux_d, &
               scratch_Hydro_hy_fluxBufX_d, &
               scratch_Hydro_hy_fluxBufY_d, &
               scratch_Hydro_hy_fluxBufZ_d, &
               scratch_Hydro_hy_flx_d, &
               scratch_Hydro_hy_fly_d, &
               scratch_Hydro_hy_flz_d, &
               scratch_Hydro_hy_grav_d, &
               scratch_Hydro_hy_rope_d, &
               scratch_Hydro_hy_starState_d, &
               scratch_Hydro_hy_tmpState_d, &
               scratch_Hydro_hy_uMinus_d, &
               scratch_Hydro_hy_uPlus_d, &
               scratch_Hydro_xCenter_fake_d, &
               scratch_Hydro_xLeft_fake_d, &
               scratch_Hydro_xRight_fake_d, &
               scratch_Hydro_yCenter_fake_d, &
               scratch_Hydro_yLeft_fake_d, &
               scratch_Hydro_yRight_fake_d, &
               scratch_Hydro_zCenter_fake_d &
         )
      use iso_c_binding, ONLY : C_PTR
      use openacc

      use Hydro_interface, ONLY : Hydro_prepBlock
      use Hydro_interface, ONLY : Hydro_advance

      !$acc routine (Hydro_prepBlock) vector
      !$acc routine (Hydro_advance) vector

      implicit none

      type(C_PTR), intent(IN) :: C_packet_h
      integer(kind=acc_handle_kind), intent(IN) :: dataQ_h
      integer, intent(IN) :: nTiles_d
      real, intent(IN) :: external_Hydro_dt_d
      real, intent(IN) :: external_Hydro_dtOld_d
      integer, intent(IN) :: external_Hydro_stage_d
      integer, intent(IN) :: tile_arrayBounds_d(:, :, :)
      real, intent(IN) :: tile_deltas_d(:, :)
      integer, intent(IN) :: tile_interior_d(:, :, :)
      integer, intent(IN) :: tile_lbound_d(:, :)
      integer, intent(IN) :: tile_lo_d(:, :)
      real, intent(INOUT) :: CC_1_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_cvol_fake_d(:, :, :, :)
      real, intent(IN) :: scratch_Hydro_fareaX_fake_d(:, :, :, :)
      real, intent(IN) :: scratch_Hydro_fareaY_fake_d(:, :, :, :)
      real, intent(IN) :: scratch_Hydro_fareaZ_fake_d(:, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_Vc_d(:, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_flat3d_d(:, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_flux_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_fluxBufX_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_fluxBufY_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_fluxBufZ_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_flx_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_fly_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_flz_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_grav_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_rope_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_starState_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_tmpState_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_uMinus_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_hy_uPlus_d(:, :, :, :, :)
      real, intent(IN) :: scratch_Hydro_xCenter_fake_d(:, :)
      real, intent(IN) :: scratch_Hydro_xLeft_fake_d(:, :)
      real, intent(IN) :: scratch_Hydro_xRight_fake_d(:, :)
      real, intent(IN) :: scratch_Hydro_yCenter_fake_d(:, :)
      real, intent(IN) :: scratch_Hydro_yLeft_fake_d(:, :)
      real, intent(IN) :: scratch_Hydro_yRight_fake_d(:, :)
      real, intent(IN) :: scratch_Hydro_zCenter_fake_d(:, :)

      integer :: n

      !$acc data &
      !$acc& deviceptr( &
      !$acc&      nTiles_d, &
      !$acc&      external_Hydro_dt_d, &
      !$acc&      external_Hydro_dtOld_d, &
      !$acc&      external_Hydro_stage_d, &
      !$acc&      tile_arrayBounds_d, &
      !$acc&      tile_deltas_d, &
      !$acc&      tile_interior_d, &
      !$acc&      tile_lbound_d, &
      !$acc&      tile_lo_d, &
      !$acc&      CC_1_d, &
      !$acc&      scratch_Hydro_cvol_fake_d, &
      !$acc&      scratch_Hydro_fareaX_fake_d, &
      !$acc&      scratch_Hydro_fareaY_fake_d, &
      !$acc&      scratch_Hydro_fareaZ_fake_d, &
      !$acc&      scratch_Hydro_hy_Vc_d, &
      !$acc&      scratch_Hydro_hy_flat3d_d, &
      !$acc&      scratch_Hydro_hy_flux_d, &
      !$acc&      scratch_Hydro_hy_fluxBufX_d, &
      !$acc&      scratch_Hydro_hy_fluxBufY_d, &
      !$acc&      scratch_Hydro_hy_fluxBufZ_d, &
      !$acc&      scratch_Hydro_hy_flx_d, &
      !$acc&      scratch_Hydro_hy_fly_d, &
      !$acc&      scratch_Hydro_hy_flz_d, &
      !$acc&      scratch_Hydro_hy_grav_d, &
      !$acc&      scratch_Hydro_hy_rope_d, &
      !$acc&      scratch_Hydro_hy_starState_d, &
      !$acc&      scratch_Hydro_hy_tmpState_d, &
      !$acc&      scratch_Hydro_hy_uMinus_d, &
      !$acc&      scratch_Hydro_hy_uPlus_d, &
      !$acc&      scratch_Hydro_xCenter_fake_d, &
      !$acc&      scratch_Hydro_xLeft_fake_d, &
      !$acc&      scratch_Hydro_xRight_fake_d, &
      !$acc&      scratch_Hydro_yCenter_fake_d, &
      !$acc&      scratch_Hydro_yLeft_fake_d, &
      !$acc&      scratch_Hydro_yRight_fake_d, &
      !$acc&      scratch_Hydro_zCenter_fake_d &
      !$acc&   )

      !$acc parallel loop gang default(none) &
      !$acc& async(dataQ_h)
      do n = 1, nTiles_d
         CALL Hydro_prepBlock( &
               CC_1_d(:, :, :, :, n), &
               scratch_Hydro_hy_Vc_d(:, :, :, n), &
               tile_arrayBounds_d(:, :, n), &
               scratch_Hydro_hy_starState_d(:, :, :, :, n), &
               scratch_Hydro_hy_tmpState_d(:, :, :, :, n), &
               external_Hydro_stage_d, &
               tile_lbound_d(:, n) &
               )
      end do
      !$acc end parallel loop

      !$acc parallel loop gang default(none) &
      !$acc& async(dataQ_h)
      do n = 1, nTiles_d
         CALL Hydro_advance( &
               CC_1_d(:, :, :, :, n), &
               external_Hydro_dt_d, &
               external_Hydro_dtOld_d, &
               scratch_Hydro_hy_starState_d(:, :, :, :, n), &
               scratch_Hydro_hy_tmpState_d(:, :, :, :, n), &
               scratch_Hydro_hy_flx_d(:, :, :, :, n), &
               scratch_Hydro_hy_fly_d(:, :, :, :, n), &
               scratch_Hydro_hy_flz_d(:, :, :, :, n), &
               scratch_Hydro_hy_fluxBufX_d(:, :, :, :, n), &
               scratch_Hydro_hy_fluxBufY_d(:, :, :, :, n), &
               scratch_Hydro_hy_fluxBufZ_d(:, :, :, :, n), &
               scratch_Hydro_hy_grav_d(:, :, :, :, n), &
               scratch_Hydro_hy_flat3d_d(:, :, :, n), &
               scratch_Hydro_hy_rope_d(:, :, :, :, n), &
               scratch_Hydro_hy_flux_d(:, :, :, :, n), &
               scratch_Hydro_hy_uPlus_d(:, :, :, :, n), &
               scratch_Hydro_hy_uMinus_d(:, :, :, :, n), &
               tile_deltas_d(:, n), &
               tile_interior_d(:, :, n), &
               tile_arrayBounds_d(:, :, n), &
               tile_lo_d(:, n), &
               tile_lbound_d(:, n), &
               scratch_Hydro_xCenter_fake_d(:, n), &
               scratch_Hydro_yCenter_fake_d(:, n), &
               scratch_Hydro_zCenter_fake_d(:, n), &
               scratch_Hydro_xLeft_fake_d(:, n), &
               scratch_Hydro_xRight_fake_d(:, n), &
               scratch_Hydro_yLeft_fake_d(:, n), &
               scratch_Hydro_yRight_fake_d(:, n), &
               scratch_Hydro_fareaX_fake_d(:, :, :, n), &
               scratch_Hydro_fareaY_fake_d(:, :, :, n), &
               scratch_Hydro_fareaZ_fake_d(:, :, :, n), &
               scratch_Hydro_cvol_fake_d(:, :, :, n) &
               )
      end do
      !$acc end parallel loop

      !$acc wait( &
      !$acc&      dataQ_h &
      !$acc&   )

      !$acc end data
   end subroutine gpu_taskfn_0_Fortran

end module gpu_taskfn_0_mod

