
!<_connector:use_interface>
use Grid_interface, ONLY: Grid_fillGuardCells
use Logfile_interface, ONLY: Logfile_stampVarMask
use Hydro_data, ONLY: hy_gcMask, &
                      hy_gcMaskSize, &
                      hy_eosModeGc

!<_connector:var_definition>
logical, SAVE :: gcMaskLogged = .FALSE.
integer       :: eosModeGc

!<_connector:var_initialization>>
eosModeGc = hy_eosModeGc


!<_connector:execute>
!!****if* FlashX_RecipeTools/TimeStepRecipe/_internal_tpl/cg-tpl.guardcell_fill
!!***
   if (.NOT.gcMaskLogged) then
      call Logfile_stampVarMask(hy_gcMask, .TRUE., '[Hydro]', 'gcNeed')
   end if

   call Grid_fillGuardCells(CENTER, ALLDIR, &
                            doEos=.TRUE., &
                            eosMode=eosModeGc, &
                            maskSize=hy_gcMaskSize, &
                            mask=hy_gcMask, &
                            makeMaskConsistent=.TRUE., &
                            selectBlockType=LEAF,      &
                            doLogMask=.NOT.gcMaskLogged)

   gcMaskLogged = .TRUE.
