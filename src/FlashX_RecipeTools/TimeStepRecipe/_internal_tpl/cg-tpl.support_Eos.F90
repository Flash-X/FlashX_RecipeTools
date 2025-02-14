
!<_connector:use_interface>
use Hydro_data, ONLY: hy_eosModeAfter


!<_connector:var_definition>
integer       :: eosMode

!<_connector:var_initialization>>
!!****if* FlashX_RecipeTools/TimeStepRecipe/_internal_tpl/cg-tpl.support_Eos
!!***
eosMode = hy_eosmodeafter
