
!<_connector:use_interface>
use Grid_interface, ONLY: Grid_zeroFluxData
use Hydro_data, ONLY: hy_fluxCorrect, &
                      hy_geometry, &
                      hy_smallE, &
                      hy_smalldens, &
                      hy_telescoping
use hy_rk_interface, ONLY: hy_rk_correctFluxes


!<_connector:var_definition>
real, pointer, dimension(:,:,:,:) :: fluxBufX, fluxBufY, fluxBufZ
real, dimension(GRID_ILO:GRID_IHI,GRID_JLO:GRID_JHI,GRID_KLO:GRID_KHI) :: fareaX, fareaY, fareaZ
real, dimension(GRID_ILO:GRID_IHI,GRID_JLO:GRID_JHI,GRID_KLO:GRID_KHI) :: cvol
real, dimension(GRID_ILO:GRID_IHI) :: xCenter, xLeft, xRight
real, dimension(GRID_JLO:GRID_JHI) :: yLeft, yRight



!<_connector:execute>


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
         !TODO: implement this
         call Driver_abort("[TimeAdvance] NotImplemented: Flux correction with curvilinear geometry")
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
      call itor%next()
   end do !!block loop
   call Grid_releaseTileIterator(itor)
   call Timers_stop("apply loop")

   call Timers_stop("flux correction")
end if !Flux correction


