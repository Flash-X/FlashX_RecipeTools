!> @copyright Copyright 2023 UChicago Argonne, LLC and contributors
!!
!! @licenseblock
!!   Licensed under the Apache License, Version 2.0 (the "License");
!!   you may not use this file except in compliance with the License.
!!
!!   Unless required by applicable law or agreed to in writing, software
!!   distributed under the License is distributed on an "AS IS" BASIS,
!!   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
!!   See the License for the specific language governing permissions and
!!   limitations under the License.
!! @endlicenseblock
!!
!! @file
!> @ingroup HydroSpark
!!
!! @brief Main implementations of Spark Hydro solver
!!
!! @stubref{Hydro}
!<
!!Reorder(4): hy_fl[xyz],hy_fluxBuf[XYZ],hy_starState,hy_tmpState,Uin
!!Reorder(4): hy_rope,hy_flux,hy_uPlus,hy_uMinus
!!NOVARIANTS
subroutine Hydro(timeEndAdv, dt, dtOld, sweepOrder)

   use Grid_interface, ONLY : Grid_getTileIterator, &
                              Grid_releaseTileIterator, &
                              Grid_getCellCoords, &
                              Grid_getCellFaceAreas, &
                              Grid_getCellVolumes, &
                              Grid_communicateFluxes, &
                              Grid_fillGuardCells, &
                              Grid_zeroFluxData, &     ! this only required for levelwidefluxes
                              Grid_getFluxCorrData_block, &
                              Grid_getFluxCorrData_xtra, &
                              Grid_putFluxData, &
                              Grid_putFluxData_block   ! this only required for nonTelescoping
   use Grid_tile, ONLY : Grid_tile_t
   use Grid_iterator, ONLY : Grid_iterator_t
   use Timers_interface, ONLY : Timers_start, Timers_stop
   use Logfile_interface, ONLY : Logfile_stampVarMask
   use Eos_interface, ONLY : Eos_multiDim
   use IO_interface, ONLY : IO_setScalar

   use Hydro_data, ONLY : hy_useHydro, &
                          hy_eosModeGc, &
                          hy_fluxCorrect, hy_fluxCorrectPerLevel, &
                          hy_telescoping, &
                          hy_maxLev, &
                          hy_weights, hy_coeffArray, &
                          hy_addFluxArray, &  ! this only required for nonTelescoping
                          hy_threadWithinBlock, hy_flattening, &
                          hy_gcMask,&
                          hy_lChyp, hy_C_hyp, hy_alphaGLM, &
                          hy_geometry, hy_tiny, hy_hybridRiemann, hy_maxCells, &
                          hy_cvisc, hy_smallE, hy_smalldens, hy_smallpres, hy_smallX, &
                          hy_limRad, hy_mp5ZeroTol
   @M hy_scratch_use

   use hy_rk_interface, ONLY : hy_rk_initSolnScratch, &
                               hy_rk_getFaceFlux, &
                               hy_rk_getGraveAccel, &
                               hy_rk_updateSoln, &
                               hy_rk_renormAbundance, &
                               hy_rk_correctFluxes, &
                               hy_rk_shockDetect, &
                               hy_rk_getFlatteningLimiter, &
                               hy_rk_saveFluxBuf

#include "Simulation.h"
#include "constants.h"
#include "Eos.h"
#include "Spark.h"

#include "Flashx_mpi_implicitNone.fh"

#define NRECON HY_NUM_VARS+NSPECIES+NMASS_SCALARS

   real, intent(IN) :: timeEndAdv, dt, dtOld
   integer, intent(IN) :: sweepOrder
   @M iter_declare(blkLimits,blkLimitsGC, grownLimits, Uin)
   integer :: level
   integer, dimension(MDIM) :: lo, loGC
   real, dimension(MDIM) :: deltas

   @M hy_declare_scr_ptr
#ifdef DEBUG_GRID_GCMASK
   logical,save :: gcMaskLogged =.FALSE.
#else
   logical,parameter :: gcMaskLogged =.TRUE.
#endif

   real :: wt

   ! telescoping variables
   integer, dimension(MDIM) :: gCells
   integer, dimension(LOW:HIGH, MDIM, NDIM, MAXSTAGE) :: lim, limgc
   integer, dimension(LOW:HIGH, MDIM, MAXSTAGE) :: limits

   integer :: i, j, k, v, lev, dir, stage, ng
   integer :: xLo, xHi, yLo, yHi, zLo, zHi

   integer, parameter :: last_stage = MAXSTAGE
   logical :: offload = .false.

   if (.NOT. hy_useHydro) return

   ! Check for some incompatible configuration options; perhaps move to Hydro_init
   @M hy_check_config

   call Timers_start("Hydro")

   @M hy_DIR_TARGET_enter_data(alloc, [deltas, grownLimits, blkLimits, blkLimitsGC, limits, lo, loGC])

   ! Find the global maximum hyperbolic speed. hy_lChyp from Hydro_computeDt
#ifdef SPARK_GLM
   call MPI_AllReduce (hy_lChyp, hy_C_hyp, 1, &
                       FLASH_REAL, MPI_MAX, hy_globalComm, error)
   call IO_setScalar("C_hyp", hy_lChyp)
#endif

   ! zero-ing level-wide flux data in case of level-wide fluxes
   ! are used for flux correction with AMReX grid.
   ! otherwise, it calls a stub so has no effect.
   if (hy_fluxCorrect) call Grid_zeroFluxData()

   stage = 1

   !--------------------------------------------------------------------
   !- Begin Hydro Sequence
   !----

   !<_link:execute>

   !----
   !- End Hydro Sequence
   !--------------------------------------------------------------------



   ! Reset local maximum hyperbolic speed. This will be updated in Hydro_computeDt.
   hy_lChyp = TINY(1.0)

   @M hy_DIR_TARGET_exit_data(release, [grownLimits, blkLimits, blkLimitsGC, limits, lo, loGC])

   call Timers_stop("Hydro")

end subroutine Hydro
