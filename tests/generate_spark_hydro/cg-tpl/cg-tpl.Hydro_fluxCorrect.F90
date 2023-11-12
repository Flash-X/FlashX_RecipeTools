! <_connector:execute>

! Store flux buffer in semipermanent flux storage (SPFS)
if ((hy_telescoping) .and. (hy_fluxCorrect)) then
   call Grid_putFluxData(tileDesc, &
                         hy_fluxBufX, &
                         hy_fluxBufY, &
                         hy_fluxBufZ, &
                         blkLimits(LOW,:))
end if
