! <_connector:execute>

if (hy_fluxCorrect) then
   wt=0.0
   if(stage > 1)wt=1.0
   @M hy_addFluxes
end if
