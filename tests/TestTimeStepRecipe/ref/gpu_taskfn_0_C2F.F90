#include "Milhoja.h"
#ifndef MILHOJA_OPENACC_OFFLOADING
#error "This file should only be compiled if using OpenACC offloading"
#endif

subroutine gpu_taskfn_0_C2F( &
C_packet_h, &
C_queue1_h, &
C_nTiles_h, &
C_nTiles_d, &
C_external_Hydro_dt_d, &
C_external_Hydro_dtOld_d, &
C_external_Hydro_stage_d, &
C_tile_arrayBounds_d, &
C_tile_deltas_d, &
C_tile_interior_d, &
C_tile_lbound_d, &
C_tile_lo_d, &
C_CC_1_d, &
C_scratch_Hydro_cvol_fake_d, &
C_scratch_Hydro_fareaX_fake_d, &
C_scratch_Hydro_fareaY_fake_d, &
C_scratch_Hydro_fareaZ_fake_d, &
C_scratch_Hydro_hy_Vc_d, &
C_scratch_Hydro_hy_flat3d_d, &
C_scratch_Hydro_hy_flux_d, &
C_scratch_Hydro_hy_fluxBufX_d, &
C_scratch_Hydro_hy_fluxBufY_d, &
C_scratch_Hydro_hy_fluxBufZ_d, &
C_scratch_Hydro_hy_flx_d, &
C_scratch_Hydro_hy_fly_d, &
C_scratch_Hydro_hy_flz_d, &
C_scratch_Hydro_hy_grav_d, &
C_scratch_Hydro_hy_rope_d, &
C_scratch_Hydro_hy_starState_d, &
C_scratch_Hydro_hy_tmpState_d, &
C_scratch_Hydro_hy_uMinus_d, &
C_scratch_Hydro_hy_uPlus_d, &
C_scratch_Hydro_xCenter_fake_d, &
C_scratch_Hydro_xLeft_fake_d, &
C_scratch_Hydro_xRight_fake_d, &
C_scratch_Hydro_yCenter_fake_d, &
C_scratch_Hydro_yLeft_fake_d, &
C_scratch_Hydro_yRight_fake_d, &
C_scratch_Hydro_zCenter_fake_d &
) bind(c, name="gpu_taskfn_0_C2F")

   use iso_c_binding, ONLY : C_PTR, C_F_POINTER
   use openacc, ONLY : acc_handle_kind
   use milhoja_types_mod, ONLY : MILHOJA_INT
   use gpu_taskfn_0_mod, ONLY : gpu_taskfn_0_Fortran
   implicit none

   type(C_PTR), intent(IN), value :: C_packet_h
   integer(MILHOJA_INT), intent(IN), value :: C_queue1_h
   integer(MILHOJA_INT), intent(IN), value :: C_nTiles_h
   type(C_PTR), intent(IN), value :: C_nTiles_d
   type(C_PTR), intent(IN), value :: C_external_Hydro_dt_d
   type(C_PTR), intent(IN), value :: C_external_Hydro_dtOld_d
   type(C_PTR), intent(IN), value :: C_external_Hydro_stage_d
   type(C_PTR), intent(IN), value :: C_tile_arrayBounds_d
   type(C_PTR), intent(IN), value :: C_tile_deltas_d
   type(C_PTR), intent(IN), value :: C_tile_interior_d
   type(C_PTR), intent(IN), value :: C_tile_lbound_d
   type(C_PTR), intent(IN), value :: C_tile_lo_d
   type(C_PTR), intent(IN), value :: C_CC_1_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_cvol_fake_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_fareaX_fake_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_fareaY_fake_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_fareaZ_fake_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_Vc_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_flat3d_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_flux_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_fluxBufX_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_fluxBufY_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_fluxBufZ_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_flx_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_fly_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_flz_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_grav_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_rope_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_starState_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_tmpState_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_uMinus_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_hy_uPlus_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_xCenter_fake_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_xLeft_fake_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_xRight_fake_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_yCenter_fake_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_yLeft_fake_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_yRight_fake_d
   type(C_PTR), intent(IN), value :: C_scratch_Hydro_zCenter_fake_d

   integer(kind=acc_handle_kind) :: F_queue1_h
   integer :: F_nTiles_h
   integer, pointer :: F_nTiles_d
   real, pointer :: F_external_Hydro_dt_d
   real, pointer :: F_external_Hydro_dtOld_d
   integer, pointer :: F_external_Hydro_stage_d
   integer, pointer :: F_tile_arrayBounds_d(:,:,:)
   real, pointer :: F_tile_deltas_d(:,:)
   integer, pointer :: F_tile_interior_d(:,:,:)
   integer, pointer :: F_tile_lbound_d(:,:)
   integer, pointer :: F_tile_lo_d(:,:)
   real, pointer :: F_CC_1_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_cvol_fake_d(:,:,:,:)
   real, pointer :: F_scratch_Hydro_fareaX_fake_d(:,:,:,:)
   real, pointer :: F_scratch_Hydro_fareaY_fake_d(:,:,:,:)
   real, pointer :: F_scratch_Hydro_fareaZ_fake_d(:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_Vc_d(:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_flat3d_d(:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_flux_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_fluxBufX_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_fluxBufY_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_fluxBufZ_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_flx_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_fly_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_flz_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_grav_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_rope_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_starState_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_tmpState_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_uMinus_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_hy_uPlus_d(:,:,:,:,:)
   real, pointer :: F_scratch_Hydro_xCenter_fake_d(:,:)
   real, pointer :: F_scratch_Hydro_xLeft_fake_d(:,:)
   real, pointer :: F_scratch_Hydro_xRight_fake_d(:,:)
   real, pointer :: F_scratch_Hydro_yCenter_fake_d(:,:)
   real, pointer :: F_scratch_Hydro_yLeft_fake_d(:,:)
   real, pointer :: F_scratch_Hydro_yRight_fake_d(:,:)
   real, pointer :: F_scratch_Hydro_zCenter_fake_d(:,:)
   
   F_queue1_h = INT(C_queue1_h, kind=acc_handle_kind)
   F_nTiles_h = INT(C_nTiles_h)
   CALL C_F_POINTER(C_nTiles_d, F_nTiles_d)
   CALL C_F_POINTER(C_external_Hydro_dt_d, F_external_Hydro_dt_d)
   CALL C_F_POINTER(C_external_Hydro_dtOld_d, F_external_Hydro_dtOld_d)
   CALL C_F_POINTER(C_external_Hydro_stage_d, F_external_Hydro_stage_d)
   CALL C_F_POINTER(C_tile_arrayBounds_d, F_tile_arrayBounds_d, shape=[2, MILHOJA_MDIM, F_nTiles_h])
   CALL C_F_POINTER(C_tile_deltas_d, F_tile_deltas_d, shape=[MILHOJA_MDIM, F_nTiles_h])
   CALL C_F_POINTER(C_tile_interior_d, F_tile_interior_d, shape=[2, MILHOJA_MDIM, F_nTiles_h])
   CALL C_F_POINTER(C_tile_lbound_d, F_tile_lbound_d, shape=[MILHOJA_MDIM, F_nTiles_h])
   CALL C_F_POINTER(C_tile_lo_d, F_tile_lo_d, shape=[MILHOJA_MDIM, F_nTiles_h])
   CALL C_F_POINTER(C_CC_1_d, F_CC_1_d, shape=[16 + 2 * 6 * MILHOJA_K1D, 16 + 2 * 6 * MILHOJA_K2D, 1 + 2 * 6 * MILHOJA_K3D, 18, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_cvol_fake_d, F_scratch_Hydro_cvol_fake_d, shape=[1, 1, 1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_fareaX_fake_d, F_scratch_Hydro_fareaX_fake_d, shape=[1, 1, 1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_fareaY_fake_d, F_scratch_Hydro_fareaY_fake_d, shape=[1, 1, 1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_fareaZ_fake_d, F_scratch_Hydro_fareaZ_fake_d, shape=[1, 1, 1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_Vc_d, F_scratch_Hydro_hy_Vc_d, shape=[28, 28, 1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_flat3d_d, F_scratch_Hydro_hy_flat3d_d, shape=[28, 28, 1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_flux_d, F_scratch_Hydro_hy_flux_d, shape=[28, 28, 1, 7, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_fluxBufX_d, F_scratch_Hydro_hy_fluxBufX_d, shape=[17, 16, 1, 5, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_fluxBufY_d, F_scratch_Hydro_hy_fluxBufY_d, shape=[16, 17, 1, 5, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_fluxBufZ_d, F_scratch_Hydro_hy_fluxBufZ_d, shape=[16, 16, 1, 5, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_flx_d, F_scratch_Hydro_hy_flx_d, shape=[28, 28, 1, 5, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_fly_d, F_scratch_Hydro_hy_fly_d, shape=[28, 28, 1, 5, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_flz_d, F_scratch_Hydro_hy_flz_d, shape=[28, 28, 1, 5, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_grav_d, F_scratch_Hydro_hy_grav_d, shape=[3, 28, 28, 1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_rope_d, F_scratch_Hydro_hy_rope_d, shape=[28, 28, 1, 7, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_starState_d, F_scratch_Hydro_hy_starState_d, shape=[28, 28, 1, 18, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_tmpState_d, F_scratch_Hydro_hy_tmpState_d, shape=[28, 28, 1, 18, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_uMinus_d, F_scratch_Hydro_hy_uMinus_d, shape=[28, 28, 1, 7, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_hy_uPlus_d, F_scratch_Hydro_hy_uPlus_d, shape=[28, 28, 1, 7, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_xCenter_fake_d, F_scratch_Hydro_xCenter_fake_d, shape=[1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_xLeft_fake_d, F_scratch_Hydro_xLeft_fake_d, shape=[1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_xRight_fake_d, F_scratch_Hydro_xRight_fake_d, shape=[1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_yCenter_fake_d, F_scratch_Hydro_yCenter_fake_d, shape=[1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_yLeft_fake_d, F_scratch_Hydro_yLeft_fake_d, shape=[1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_yRight_fake_d, F_scratch_Hydro_yRight_fake_d, shape=[1, F_nTiles_h])
   CALL C_F_POINTER(C_scratch_Hydro_zCenter_fake_d, F_scratch_Hydro_zCenter_fake_d, shape=[1, F_nTiles_h])

   CALL gpu_taskfn_0_Fortran ( &
      C_packet_h, &
      F_queue1_h, &
      F_nTiles_d, &
      F_external_Hydro_dt_d, &
      F_external_Hydro_dtOld_d, &
      F_external_Hydro_stage_d, &
      F_tile_arrayBounds_d, &
      F_tile_deltas_d, &
      F_tile_interior_d, &
      F_tile_lbound_d, &
      F_tile_lo_d, &
      F_CC_1_d, &
      F_scratch_Hydro_cvol_fake_d, &
      F_scratch_Hydro_fareaX_fake_d, &
      F_scratch_Hydro_fareaY_fake_d, &
      F_scratch_Hydro_fareaZ_fake_d, &
      F_scratch_Hydro_hy_Vc_d, &
      F_scratch_Hydro_hy_flat3d_d, &
      F_scratch_Hydro_hy_flux_d, &
      F_scratch_Hydro_hy_fluxBufX_d, &
      F_scratch_Hydro_hy_fluxBufY_d, &
      F_scratch_Hydro_hy_fluxBufZ_d, &
      F_scratch_Hydro_hy_flx_d, &
      F_scratch_Hydro_hy_fly_d, &
      F_scratch_Hydro_hy_flz_d, &
      F_scratch_Hydro_hy_grav_d, &
      F_scratch_Hydro_hy_rope_d, &
      F_scratch_Hydro_hy_starState_d, &
      F_scratch_Hydro_hy_tmpState_d, &
      F_scratch_Hydro_hy_uMinus_d, &
      F_scratch_Hydro_hy_uPlus_d, &
      F_scratch_Hydro_xCenter_fake_d, &
      F_scratch_Hydro_xLeft_fake_d, &
      F_scratch_Hydro_xRight_fake_d, &
      F_scratch_Hydro_yCenter_fake_d, &
      F_scratch_Hydro_yLeft_fake_d, &
      F_scratch_Hydro_yRight_fake_d, &
      F_scratch_Hydro_zCenter_fake_d &
   )
end subroutine gpu_taskfn_0_C2F

