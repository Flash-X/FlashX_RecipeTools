! <_connector:execute>

!Once the finest level is completed, place averaged fine fluxes into
!current coarse semipermanent flux storage (SPFS)
if (lev < hy_maxLev) call Grid_communicateFluxes(ALLDIR,lev)
