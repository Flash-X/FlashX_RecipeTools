
!<_connector:use_interface>
use Grid_interface, ONLY: Grid_zeroFluxData, &
                          Grid_getCellVolumes, &
                          Grid_getCellFaceAreas, &
                          Grid_getCellCoords
use Hydro_data, ONLY: hy_fluxCorrect, &
                      hy_geometry, &
                      hy_smallE, &
                      hy_smalldens, &
                      hy_telescoping
use hy_rk_interface, ONLY: hy_rk_correctFluxes


!<_connector:var_definition>
integer :: level
real, pointer, dimension(:,:,:,:) :: fluxBufX, fluxBufY, fluxBufZ
real, dimension(:, :, :), allocatable :: cvol, fareaX, fareaY, fareaZ
real, dimension(:), allocatable :: xCenter, xLeft, xRight
real, dimension(:), allocatable :: yLeft, yRight



!<_connector:execute>
!!****if* FlashX_RecipeTools/TimeStepRecipe/_internal_tpl/cg-tpl.fluxCorrection
!!***
! flux correction for Spark with Milhoja
if (hy_fluxCorrect) then
   call Grid_zeroFluxData()
   call Timers_start("flux correction")

   !Store flux buffer in semipermanent flux storage (SPFS)
   nullify(fluxBufX); nullify(fluxBufY); nullify(fluxBufZ);
   call Timers_start("put loop")
   call Grid_getTileIterator(itor, LEAF, tiling=.false.)
   do while(itor%isValid())
      call itor%currentTile(tileDesc)
      blkLimits(:, :) = tileDesc%limits
      call tileDesc%getDataPtr(fluxBufX, FLUXX)
      call tileDesc%getDataPtr(fluxBufY, FLUXY)
      call tileDesc%getDataPtr(fluxBufZ, FLUXZ)
      call Grid_putFluxData( &
         tileDesc, &
         fluxBufX, &
         fluxBufY, &
         fluxBufZ, &
         blkLimits(LOW, :) &
      )
      call tileDesc%releaseDataPtr(fluxBufX, FLUXX)
      call tileDesc%releaseDataPtr(fluxBufY, FLUXY)
      call tileDesc%releaseDataPtr(fluxBufZ, FLUXZ)
      call itor%next()
   end do
   call Grid_releaseTileIterator(itor)
   call Timers_stop("put loop")


   !Communicate the fine fluxes
   call Timers_start("communicate")
   call Grid_communicateFluxes(ALLDIR, UNSPEC_LEVEL)
   call Timers_stop("communicate")


   nullify (Uin)
   nullify(fluxBufX); nullify(fluxBufY); nullify(fluxBufZ);
   call Timers_start("apply loop")
   call Grid_getTileIterator(itor, LEAF, tiling=.false.)
   do while (itor%isValid())
      call itor%currentTile(tileDesc)
      blkLimits(:, :) = tileDesc%limits
      blkLimitsGC(:, :) = tileDesc%blkLimitsGC
      grownLimits(:, :) = tileDesc%grownLimits
      lo(:) = blkLimits(LOW, :)
      loGC(:) = blkLimitsGC(LOW, :)
      hi(:) = blkLimits(HIGH, :)
      hiGC(:) = blkLimitsGC(HIGH, :)
      level = tileDesc%level
      call tileDesc%deltas(deltas)
      call tileDesc%getDataPtr(Uin, CENTER)
      call tileDesc%getDataPtr(fluxBufX, FLUXX)
      call tileDesc%getDataPtr(fluxBufY, FLUXY)
      call tileDesc%getDataPtr(fluxBufZ, FLUXZ)

      call Grid_getFluxCorrData_block( &
         tileDesc, &
         fluxBufX, &
         fluxBufY, &
         fluxBufZ, &
         blkLimits(LOW, :), &
         isFluxDensity=(/hy_telescoping/) &
      )

      if (hy_geometry /= CARTESIAN) then
         allocate( cvol(loGC(IAXIS):hiGC(IAXIS), &
                        loGC(JAXIS):hiGC(JAXIS), &
                        loGC(KAXIS):hiGC(KAXIS)) )
         allocate( fareaX(loGC(IAXIS):hiGC(IAXIS), &
                          loGC(JAXIS):hiGC(JAXIS), &
                          loGC(KAXIS):hiGC(KAXIS)) )
         allocate( fareaY(loGC(IAXIS):hiGC(IAXIS), &
                          loGC(JAXIS):hiGC(JAXIS), &
                          loGC(KAXIS):hiGC(KAXIS)) )
         allocate( fareaZ(loGC(IAXIS):hiGC(IAXIS), &
                          loGC(JAXIS):hiGC(JAXIS), &
                          loGC(KAXIS):hiGC(KAXIS)) )
         allocate( xCenter(loGC(IAXIS):hiGC(IAXIS)) )
         allocate( xLeft(loGC(IAXIS):hiGC(IAXIS)) )
         allocate( xRight(loGC(IAXIS):hiGC(IAXIS)) )
         allocate( yLeft(loGC(JAXIS):hiGC(JAXIS)) )
         allocate( yRight(loGC(JAXIS):hiGC(JAXIS)) )

         call Grid_getCellVolumes(level, loGC, hiGC, cvol)
         call Grid_getCellFaceAreas(IAXIS, level, loGC, hiGC, fareaX)
         call Grid_getCellFaceAreas(JAXIS, level, loGC, hiGC, fareaY)
         call Grid_getCellFaceAreas(KAXIS, level, loGC, hiGC, fareaZ)
         call Grid_getCellCoords(IAXIS, CENTER, level, loGC, hiGC, xCenter)
         call Grid_getCellCoords(IAXIS, LEFT_EDGE, level, loGC, hiGC, xLeft)
         call Grid_getCellCoords(IAXIS, RIGHT_EDGE, level, loGC, hiGC, xRight)
         call Grid_getCellCoords(JAXIS, LEFT_EDGE, level, loGC, hiGC, yLeft)
         call Grid_getCellCoords(JAXIS, RIGHT_EDGE, level, loGC, hiGC, yRight)
      end if

      call hy_rk_correctFluxes( &
         Uin, blkLimits, &
         fluxBufX, fluxBufY, fluxBufZ, &
         deltas, fareaX, fareaY, fareaZ, cvol, xCenter, &
         xLeft, xRight, yLeft, yRight, &
         hy_geometry, &
         hy_smallE, hy_smalldens, &
         dt, .NOT. hy_telescoping, &
         lo, loGC &
      )
      call tileDesc%releaseDataPtr(fluxBufX, FLUXX)
      call tileDesc%releaseDataPtr(fluxBufY, FLUXY)
      call tileDesc%releaseDataPtr(fluxBufZ, FLUXZ)
      call tileDesc%releaseDataPtr(Uin, CENTER)

      if (hy_geometry /= CARTESIAN) then
         deallocate(cvol)
         deallocate(fareaX)
         deallocate(fareaY)
         deallocate(fareaZ)
         deallocate(xCenter)
         deallocate(xLeft)
         deallocate(xRight)
         deallocate(yLeft)
         deallocate(yRight)
      end if

      call itor%next()
   end do !!block loop
   call Grid_releaseTileIterator(itor)
   call Timers_stop("apply loop")

   call Timers_stop("flux correction")
end if !Flux correction


