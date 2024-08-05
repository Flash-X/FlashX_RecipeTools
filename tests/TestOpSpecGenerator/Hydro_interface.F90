!!****h* source/physics/Hydro/Hydro_interface
!! NOTICE
!!  Copyright 2022 UChicago Argonne, LLC and contributors
!!
!!  Licensed under the Apache License, Version 2.0 (the "License");
!!  you may not use this file except in compliance with the License.
!!
!!  Unless required by applicable law or agreed to in writing, software
!!  distributed under the License is distributed on an "AS IS" BASIS,
!!  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
!!  See the License for the specific language governing permissions and
!!  limitations under the License.
!!
!! This is the header file for the hydro module that defines its
!! public interfaces.
!!***
!!NOVARIANTS
Module Hydro_interface
#include "constants.h"
#include "Simulation.h"

   implicit none

   interface
      subroutine Hydro_computeDt(tileDesc, &
                                 x, dx, uxgrid, &
                                 y, dy, uygrid, &
                                 z, dz, uzgrid, &
                                 blkLimits, blkLimitsGC, &
                                 solnData, &
                                 dt_check, dt_minloc, extraInfo)
         use Grid_tile, ONLY: Grid_tile_t
         implicit none
         type(Grid_tile_t), intent(IN) :: tileDesc
         integer, dimension(LOW:HIGH, MDIM), intent(IN) :: blkLimits, blkLimitsGC
         real, dimension(blkLimitsGC(LOW, IAXIS):blkLimitsGC(HIGH, IAXIS)), intent(IN) :: x, dx, uxgrid
         real, dimension(blkLimitsGC(LOW, JAXIS):blkLimitsGC(HIGH, JAXIS)), intent(IN) :: y, dy, uygrid
         real, dimension(blkLimitsGC(LOW, KAXIS):blkLimitsGC(HIGH, KAXIS)), intent(IN) :: z, dz, uzgrid
         real, INTENT(INOUT)    :: dt_check
         integer, INTENT(INOUT)    :: dt_minloc(5)
         real, pointer :: solnData(:, :, :, :)
         real, OPTIONAL, intent(INOUT) :: extraInfo
      end subroutine Hydro_computeDt
   end interface

   interface
      subroutine Hydro_consolidateCFL
      end subroutine Hydro_consolidateCFL
   end interface

   interface

      subroutine Hydro_prepareBuffers()
         implicit none
      end subroutine Hydro_prepareBuffers
      subroutine Hydro_freeBuffers()
         implicit none
      end subroutine Hydro_freeBuffers

   end interface

   interface
      subroutine Hydro(timeEndAdv, dt, dtOld, sweepOrder)
         real, INTENT(IN) :: timeEndAdv, dt, dtOld
         integer, optional, INTENT(IN) :: sweepOrder
      end subroutine Hydro
   end interface

   interface
      subroutine Hydro_init()
      end subroutine Hydro_init
   end interface

   interface
      subroutine Hydro_finalize()
      end subroutine Hydro_finalize
   end interface

   interface
      subroutine Hydro_detectShock(solnData, shock, blkLimits, blkLimitsGC, &
                                   guardCells, &
                                   primaryCoord, secondCoord, thirdCoord)

         integer, intent(IN), dimension(LOW:HIGH, MDIM) :: blkLimits, blkLimitsGC
         integer, intent(IN) :: guardCells(MDIM)
         real, pointer, dimension(:, :, :, :) :: solnData
#ifdef FIXEDBLOCKSIZE
         real, intent(out), dimension(GRID_ILO_GC:GRID_IHI_GC, &
                                      GRID_JLO_GC:GRID_JHI_GC, &
                                      GRID_KLO_GC:GRID_KHI_GC):: shock
         real, intent(IN), dimension(GRID_ILO_GC:GRID_IHI_GC) :: primaryCoord
         real, intent(IN), dimension(GRID_JLO_GC:GRID_JHI_GC) :: secondCoord
         real, intent(IN), dimension(GRID_KLO_GC:GRID_KHI_GC) :: thirdCoord
#else
         real, intent(out), dimension(blkLimitsGC(LOW, IAXIS):blkLimitsGC(HIGH, IAXIS), &
                                      blkLimitsGC(LOW, JAXIS):blkLimitsGC(HIGH, JAXIS), &
                                      blkLimitsGC(LOW, KAXIS):blkLimitsGC(HIGH, KAXIS)) :: shock
         real, intent(IN), dimension(blkLimitsGC(LOW, IAXIS):blkLimitsGC(HIGH, IAXIS)) :: primaryCoord
         real, intent(IN), dimension(blkLimitsGC(LOW, JAXIS):blkLimitsGC(HIGH, JAXIS)) :: secondCoord
         real, intent(IN), dimension(blkLimitsGC(LOW, KAXIS):blkLimitsGC(HIGH, KAXIS)) :: thirdCoord
#endif

      end subroutine Hydro_detectShock
   end interface

   interface
      subroutine Hydro_shockStrength(solnData, shock, lo, hi, loHalo, hiHalo, &
                                     primaryCoord, secondCoord, thirdCoord, &
                                     threshold, mode)
         implicit none
         integer, intent(IN), dimension(1:MDIM) :: lo, hi, loHalo, hiHalo
         real, pointer :: solnData(:, :, :, :)
         real, intent(inout), dimension(loHalo(IAXIS):hiHalo(IAXIS), &
                                        loHalo(JAXIS):hiHalo(JAXIS), &
                                        loHalo(KAXIS):hiHalo(KAXIS)) :: shock
         real, intent(IN), dimension(loHalo(IAXIS):hiHalo(IAXIS)) :: primaryCoord
         real, intent(IN), dimension(loHalo(JAXIS):hiHalo(JAXIS)) :: secondCoord
         real, intent(IN), dimension(loHalo(KAXIS):hiHalo(KAXIS)) :: thirdCoord
         real, intent(IN) :: threshold
         integer, intent(IN) :: mode
      end subroutine Hydro_shockStrength
   end interface

   interface
      subroutine Hydro_sendOutputData()

      end subroutine Hydro_sendOutputData
   end interface

   interface
      logical function Hydro_gravPotIsAlreadyUpdated()
         implicit none
      end function Hydro_gravPotIsAlreadyUpdated
   end interface

   interface
      subroutine Hydro_mapBcType(bcTypeToApply, bcTypeFromGrid, varIndex, gridDataStruct, &
                                 axis, face, idest)
         implicit none
         integer, intent(OUT) :: bcTypeToApply
         integer, intent(in) :: bcTypeFromGrid, varIndex, gridDataStruct, axis, face
         integer, intent(IN), OPTIONAL:: idest
      end subroutine Hydro_mapBcType
   end interface

   !! MoL-specific functionality

   interface
      subroutine Hydro_molExplicitRHS(t, activeRHS, dtWeight)
         implicit none
         real, intent(in) :: t
         integer, intent(in) :: activeRHS
         real, intent(in) :: dtWeight
      end subroutine Hydro_molExplicitRHS
   end interface

   interface
      subroutine Hydro_molImplicitRHS(t, activeRHS, dtWeight)
         implicit none
         real, intent(in) :: t
         integer, intent(in) :: activeRHS
         real, intent(in) :: dtWeight
      end subroutine Hydro_molImplicitRHS
   end interface

   interface
      subroutine Hydro_molFastRHS(t, activeRHS, dtWeight)
         implicit none
         real, intent(in) :: t
         integer, intent(in) :: activeRHS
         real, intent(in) :: dtWeight
      end subroutine Hydro_molFastRHS
   end interface

   interface
      subroutine Hydro_molImplicitUpdate(t, dt)
         implicit none
         real, intent(in) :: t, dt
      end subroutine Hydro_molImplicitUpdate
   end interface

   interface
      subroutine Hydro_molPostUpdate(t)
         implicit none
         real, intent(in) :: t
      end subroutine Hydro_molPostUpdate
   end interface

   interface
      subroutine Hydro_molPostFastUpdate(t)
         implicit none
         real, intent(in) :: t
      end subroutine Hydro_molPostFastUpdate
   end interface

   interface
      subroutine Hydro_molPreEvolve(t)
         implicit none
         real, intent(in) :: t
      end subroutine Hydro_molPreEvolve
   end interface

   interface
      subroutine Hydro_molPostTimeStep(t)
         implicit none
         real, intent(in) :: t
      end subroutine Hydro_molPostTimeStep
   end interface

   interface
      subroutine Hydro_molPostRegrid(t)
         implicit none
         real, intent(in) :: t
      end subroutine Hydro_molPostRegrid
   end interface

   interface
      subroutine Hydro_prepGlobal(hy_gcMask, hy_eosModeGc)
         implicit none
         integer, intent(IN) :: hy_eosModeGc
         logical, dimension(NUNK_VARS), intent(IN) :: hy_gcMask
      end subroutine Hydro_prepGlobal
   end interface

#define MILHOJA_BLOCK_GC GRID_IHI_GC, GRID_JHI_GC, GRID_KHI_GC
#define MILHOJA_BLOCK GRID_IHI, GRID_JHI, GRID_KHI
#define MILHOJA_SCRATCH_GC(_VARS) source=scratch, extents=[MILHOJA_BLOCK_GC, _VARS], lbound=[tile_lbound, 1]

#include "Spark.h"

   !!milhoja begin common
   !!   _Uin :: source=grid_data, &
   !!           structure_index=[center, 1], &
   !!           RW=[1:NUNK_VARS]
   !!   _blkLimits :: source=tile_interior
   !!   _blkLimitsGC :: source=tile_arrayBounds
   !!   _lo :: source=tile_lo
   !!   _loGC :: source=tile_lbound
   !!   _hy_starState :: source=scratch, &
   !!                    extents=[MILHOJA_BLOCK_GC, NUNK_VARS], &
   !!                    lbound=[tile_lbound, 1]
   !!   _hy_tmpState :: source=scratch, &
   !!                   extents=[MILHOJA_BLOCK_GC, NUNK_VARS], &
   !!                   lbound=[tile_lbound, 1]
   !!   _stage :: source=external, &
   !!             origin=local:stage
   !!   _dt :: source=external, &
   !!          origin=input_arg:dt
   !!   _dtOld :: source=external, &
   !!             origin=input_arg:dtOld
   !!   _xCenter_fake :: source=scratch, &
   !!                    extents=[1], &
   !!                    lbound=[1]
   !!   _yCenter_fake :: source=scratch, &
   !!                    extents=[1], &
   !!                    lbound=[1]
   !!   _zCenter_fake :: source=scratch, &
   !!                    extents=[1], &
   !!                    lbound=[1]
   !!   _xLeft_fake :: source=scratch, &
   !!                  extents=[1], &
   !!                  lbound=[1]
   !!   _xRight_fake :: source=scratch, &
   !!                   extents=[1], &
   !!                   lbound=[1]
   !!   _yLeft_fake :: source=scratch, &
   !!                  extents=[1], &
   !!                  lbound=[1]
   !!   _yRight_fake :: source=scratch, &
   !!                   extents=[1], &
   !!                   lbound=[1]
   !!   _fareaX_fake :: source=scratch, &
   !!                   extents=[1, 1, 1], &
   !!                   lbound=[1, 1, 1]
   !!   _fareaY_fake :: source=scratch, &
   !!                   extents=[1, 1, 1], &
   !!                   lbound=[1, 1, 1]
   !!   _fareaZ_fake :: source=scratch, &
   !!                   extents=[1, 1, 1], &
   !!                   lbound=[1, 1, 1]
   !!   _cvol_fake :: source=scratch, &
   !!                 extents=[1, 1, 1], &
   !!                 lbound=[1, 1, 1]
   !!milhoja end common

   interface
      !!milhoja begin
      !!  Uin :: common=_Uin
      !!  hy_Vc :: source=scratch, &
      !!           extents=[MILHOJA_BLOCK_GC], &
      !!           lbound=[tile_lbound]
      !!  blkLimitsGC :: common=_blkLimitsGC
      !!  hy_starState :: common=_hy_starState
      !!  hy_tmpState :: common=_hy_tmpState
      !!  stage :: common=_stage
      !!  loGC :: common=_loGC
      subroutine Hydro_prepBlock(Uin, hy_Vc, blkLimitsGC, hy_starState, hy_tmpState, &
                                 stage, loGC)
         implicit none
         integer, intent(IN) :: loGC(3)
         real, dimension(1:, loGC(1):, loGC(2):, loGC(3):), intent(IN OUT) :: Uin
         real, dimension(1:, loGC(1):, loGC(2):, loGC(3):), intent(OUT) :: hy_starState, hy_tmpState
         real, dimension(loGC(1):, loGC(2):, loGC(3):), intent(OUT) :: hy_Vc
         integer, dimension(LOW:HIGH, MDIM), intent(IN) :: blkLimitsGC
         integer, intent(IN) :: stage
      end subroutine Hydro_prepBlock
      !!milhoja end
   end interface

   interface
      !!milhoja begin
      !!   Uin :: common=_Uin
      !!   dt :: common=_dt
      !!   dtOld :: common=_dtOld
      !!   hy_starState :: common=_hy_starState
      !!   hy_tmpState :: common=_hy_tmpState
      !!   hy_flx :: MILHOJA_SCRATCH_GC(NFLUXES)
      !!   hy_fly :: MILHOJA_SCRATCH_GC(NFLUXES)
      !!   hy_flz :: MILHOJA_SCRATCH_GC(NFLUXES)
      !!   hy_fluxBufX :: source=scratch, &
      !!                  extents=[NXB+K1D, NYB, NZB, NFLUXES], &
      !!                  lbound=[tile_lo, 1]
      !!   hy_fluxBufY :: source=scratch, &
      !!                  extents=[NXB, NYB+K2D, NZB, NFLUXES], &
      !!                  lbound=[tile_lo, 1]
      !!   hy_fluxBufZ :: source=scratch, &
      !!                  extents=[NXB, NYB, NZB+K3D, NFLUXES], &
      !!                  lbound=[tile_lo, 1]
      !!   hy_grav :: source=scratch, &
      !!              extents=[3, MILHOJA_BLOCK_GC], &
      !!              lbound=[1, tile_lbound]
      !!   hy_flat3d :: source=scratch, &
      !!                extents=[MILHOJA_BLOCK_GC], &
      !!                lbound=[tile_lbound]
      !!   hy_rope :: MILHOJA_SCRATCH_GC(NRECON)
      !!   hy_flux :: MILHOJA_SCRATCH_GC(NRECON)
      !!   hy_uPlus :: MILHOJA_SCRATCH_GC(NRECON)
      !!   hy_uMinus :: MILHOJA_SCRATCH_GC(NRECON)
      !!   deltas :: source=tile_deltas
      !!   blkLimits :: common=_blkLimits
      !!   blkLimitsGC :: common=_blkLimitsGC
      !!   lo :: common=_lo
      !!   loGC :: common=_loGC
      !!   hy_xCenter :: common=_xCenter_fake
      !!   hy_yCenter :: common=_yCenter_fake
      !!   hy_zCenter :: common=_zCenter_fake
      !!   hy_xLeft :: common=_xLeft_fake
      !!   hy_xRight :: common=_xRight_fake
      !!   hy_yLeft :: common=_yLeft_fake
      !!   hy_yRight :: common=_yRight_fake
      !!   hy_fareaX :: common=_fareaX_fake
      !!   hy_fareaY :: common=_fareaY_fake
      !!   hy_fareaZ :: common=_fareaZ_fake
      !!   hy_cvol :: common=_cvol_fake
      subroutine Hydro_advance(Uin, dt, dtOld, &
                               hy_starState, hy_tmpState, &
                               hy_flx, hy_fly, hy_flz, &
                               hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ, &
                               hy_grav, hy_flat3d, &
                               hy_rope, hy_flux, hy_uPlus, hy_uMinus, &
                               deltas, &
                               blkLimits, blkLimitsGC, &
                               lo, loGC, &
                               hy_xCenter, hy_yCenter, hy_zCenter, &
                               hy_xLeft, hy_xRight, hy_yLeft, hy_yRight, &
                               hy_fareaX, hy_fareaY, hy_fareaZ, hy_cvol)
         implicit none
         integer, intent(IN) :: lo(3), loGC(3)
         real, dimension(1:, loGC(1):, loGC(2):, loGC(3):), intent(IN OUT) :: Uin
         real, intent(IN) :: dt, dtOld
         real, dimension(1:, loGC(1):, loGC(2):, loGC(3):), intent(IN OUT) :: hy_starState
         real, dimension(1:, loGC(1):, loGC(2):, loGC(3):), intent(OUT) :: hy_flx, hy_fly, hy_flz
         real, dimension(1:, loGC(1):, loGC(2):, loGC(3):), intent(IN) :: hy_tmpState
         real, dimension(1:, lo(1):, lo(2):, lo(3):), intent(OUT) :: hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ
         real, dimension(1:, loGC(1):, loGC(2):, loGC(3):), intent(OUT) :: hy_rope, hy_flux, hy_uPlus, hy_uMinus
         real, dimension(1:, loGC(1):, loGC(2):, loGC(3):), intent(OUT) :: hy_grav
         real, dimension(loGC(1):, loGC(2):, loGC(3):), intent(OUT) :: hy_flat3d

         integer, dimension(LOW:HIGH, MDIM), intent(IN) :: blkLimits, blkLimitsGC

         real, dimension(MDIM), intent(IN)  :: deltas
         real, dimension(loGC(1):), intent(IN) :: hy_xCenter
         real, dimension(loGC(2):), intent(IN) :: hy_yCenter
         real, dimension(loGC(3):), intent(IN) :: hy_zCenter
         real, dimension(loGC(1):), intent(IN) :: hy_xLeft, hy_xRight
         real, dimension(loGC(2):), intent(IN) :: hy_yLeft, hy_yRight
         real, dimension(loGC(1):, loGC(2):, loGC(3):), intent(IN) :: hy_fareaX, hy_fareaY, hy_fareaZ, hy_cvol
      end subroutine Hydro_advance
      !!milhoja end
   end interface

   interface
      subroutine Hydro_correctSoln(dt, tileDesc, Uin, &
                                   hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ, &
                                   blkLimits, &
                                   lo, loGC, &
                                   deltas, hy_fareaX, hy_fareaY, hy_fareaZ, hy_cvol, &
                                   hy_xCenter, hy_xLeft, hy_xRight, hy_yLeft, hy_yRight, &
                                   hy_geometry, hy_telescoping, &
                                   hy_smallE, hy_smalldens)
         use Grid_tile, ONLY: Grid_tile_t
         implicit none
         real, intent(IN) :: dt
         integer, intent(IN) :: lo(3), loGC(3)
         type(Grid_tile_t), intent(IN) :: tileDesc
         real, dimension(:, :, :, :), pointer :: Uin

         real, dimension(1:, lo(1):, lo(2):, lo(3):), intent(IN OUT) :: hy_fluxBufX, hy_fluxBufY, hy_fluxBufZ

         integer, dimension(LOW:HIGH, MDIM), intent(IN) :: blkLimits
         real, dimension(MDIM), intent(IN)  :: deltas
         real, dimension(loGC(1):, loGC(2):, loGC(3):), intent(IN) :: hy_fareaX, hy_fareaY, hy_fareaZ, hy_cvol
         real, dimension(loGC(1):), intent(IN) :: hy_xCenter
         real, dimension(loGC(1):), intent(IN) :: hy_xLeft, hy_xRight
         real, dimension(loGC(2):), intent(IN) :: hy_yLeft, hy_yRight

         real, intent(IN) :: hy_smallE, hy_smalldens
         integer, intent(IN) :: hy_geometry
         logical, intent(IN) :: hy_telescoping
      end subroutine Hydro_correctSoln
   end interface
end Module Hydro_interface
