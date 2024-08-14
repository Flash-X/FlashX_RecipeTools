User's Manual
=============

Fortran Subroutine Annotation Syntax
------------------------------------

In order for the code generation tools to work, they need to make use of various
operation specifications created from existing Fortran code. However, it's difficult
to parse all of the information necessary for generating operation specifications.
Therefore, we have developed a subroutine annotation syntax for pulling the necessary
information for generating operation specifications.

*Note*: Fortran is not case-sensitive, but the keywords inside of the annotation
syntax are case sensitive. This is because the operation specfications and Task
Function Specifications defined inside of the Milhoja pypackage documentation
cannot assume what language they are generating code for (C++ or Fortran). While
names that are annotation inside of each interface file are case-insensitive, 
the keywords are not. Ensure that the case of the keywords is correct before calling
any code generation tools.

Generally, any valid keyword used by the Milhoja pypackage for code generation
is a valid keyword inside of this annotation syntax.

Variable Annotation
'''''''''''''''''''

In order to develop an operation specification, the user needs to annotate all
of the variables that they want placed inside of a Data Packet, as well as any
variable that is defined inside of the dummy argument list of all subroutines.
Annotation a variable uses the following format:

!! variable_name :: attribute_name1=value1, &
!!                  attribute_name2=[low : high], &
!!                  attribute_name3=value3 ...

Where the values of each attribute are strings, integer, or array values. Arrays
are surrounded by square brackets. Notice that if the user is declaring attributes
across multiple lines, they will need to use '&' as the line continuation character.

Attributes
""""""""""

The most important part of variable annotations are the list of attributes that
need to be associated with a variable.

Souce Attribute
^^^^^^^^^^^^^^^

This is the most important attribute to determine when annotating variables, and
is expected on every variable that needs to be annotated. There are a few different
accepted values for the source attribute. These are case-sensitive. All sources
have a list of required attributes that need to be included inside the variable
annotation if that source is being used. The list of valid sources includes:

• `external`
    * Variables that need to come from the driver code, passed into data packets via constructor
    * Can be used for constants, things like delta time.
    * Required attributes: `origin`
        * `origin`: Tells the recipe tool where the input argument is obtained
          from inside of the generated code, so that it can pass the argument into
          the generated Data Item constructor.

* "tile" sources
    * Number of different "tile" type sources, these pull data from the tile descriptor.
    * Required attributes: None

* `lbound`
    * Variables that are lower bounds of array variables
    * Required attributes: `array`
        * `array`: The array that this lower bound is associated with. Should be
                   an existing variable name that is an array.

* `grid_data`
    * Source for grid arrays, generally solution data or face arrays.
    * Required attributes: `structure_index`
        * `structure_index`: An array where the first element is some grid data
                             array {"CENTER", "FACEX", "FACEY", "FACEZ"}, and the
                             second element is the index (always 1 for now).
                             Ex: ["CENTER", 1]
    * Optional attributes: `r`, `rw`, `w`
        * All optional attributes are an array containing a range of indices.
          Must be contiguous.
        * `r`: The indices to read.
        * `w`: The indices to write
        * `rw`: The indices to read and write.

* `scratch`
    * Variable is array data that is allocated on the device and used as scratch memory.
    * Required attributes: `extents`, `lbound`
        * `extents`: An array containing the size of each dimension in the array.
                     Ex: [NXB, NYB, NZB, NFLUXES] or [16, 16, 16, 5]. Only integers
                     are accepted. Can use the preprocessor to fill in values.
        * `lbound`: The lower bound of the array. Ex: [tile_lo, 1]. `tile_lo`
                    is a special keyword that inserts the lo array contained inside
                    of a tile, and is a 3 dimensional array. The dimensionality
                    of lbound must match the dimensionality of `extents`, and as
                    such the array that this annotation is for.

Common attribute
^^^^^^^^^^^^^^^^

The second most important attribute. If a variable that is defined inside of a
subroutine block is a variable that is passed into multiple other subroutines,
then that variable needs to be defined inside of a common block. For any variable
inside of a subroutine that is defined inside of a common block, the only attribute
inside of the annotation should be a `common`, where the value is the name of the
associated variable inside the common block.

Ex: `!! dt :: common=_common_dt`

Block Types
'''''''''''

There are two types of blocks that the annotation syntax uses, common and subroutine
blocks.

Common Blocks
"""""""""""""

Common blocks are blocks that contain annotations of variables that are passed
into multiple different subroutines. Common blocks always go above all subroutine
blocks, because subroutine blocks rely on information found inside of the common block.
Common blocks are surrounded by `!!milhoja begin common` and `!!milhoja end common`
statements. All variable annotations go inbetween.

Ex:
!!milhoja begin common
!!   _Uin :: source=grid_data, &
!!           structure_index=[center, 1], &
!!           RW=[1:NUNK_VARS]
!!   _blkLimits :: source=tile_interior
!!   _blkLimitsGC :: source=tile_arrayBounds
!!   _lo :: source=tile_lo
!!   _loGC :: source=tile_lbound
!!   _hy_starState :: source=scratch, &
!!                    type=real, &
!!                    extents=[MILHOJA_BLOCK_GC, NUNK_VARS], &
!!                    lbound=[tile_lbound, 1]
!!   _hy_tmpState :: source=scratch, &
!!                   type=real, &
!!                   extents=[MILHOJA_BLOCK_GC, NUNK_VARS], &
!!                   lbound=[tile_lbound, 1]
!!   _stage :: source=external, &
!!             type=integer, &
!!             origin=local:stage
!!   _dt :: source=external, &
!!          type=real, &
!!          origin=input_arg:dt
!!milhoja end common

Subroutine Blocks
"""""""""""""""""

Subroutine blocks are annotation blocks that contain annotations of each variable
inside of the dummy argument list. In order to annotate a subroutine, surround the
subroutine with `!!milhoja begin` and `!!milhoja end` statements. Then, place every
variable annotation between the `!!milhoja begin` statement, and the line that
contains the subroutine keyword for the subroutine.

Ex:
interface
    !!milhoja begin
    !!  Uin :: common=_Uin
    !!  hy_Vc :: source=scratch, &
    !!           type=real, &
    !!           extents=[MILHOJA_BLOCK_GC], &
    !!           lbound=[tile_lbound]
    !!  blkLimits :: common=_blkLimits
    !!  blkLimitsGC :: common=_blkLimitsGC
    !!  hy_starState :: common=_hy_starState
    !!  hy_tmpState :: common=_hy_tmpState
    !!  stage :: common=_stage
    !!  lo :: common=_lo
    !!  loGC :: common=_loGC
    subroutine Hydro_prepBlock(Uin, hy_Vc, blkLimits, blkLimitsGC, hy_starState, hy_tmpState, &
                            stage, lo, loGC)
        implicit none
        integer, intent(IN) :: lo(3), loGC(3)
        real, dimension(1:, loGC(1):, loGC(2):, loGC(3):), intent(IN OUT) :: Uin
        real, dimension(1:, loGC(1):, loGC(2):, loGC(3):), intent(OUT) :: hy_starState, hy_tmpState
        real, dimension(loGC(1):, loGC(2):, loGC(3):), intent(OUT) :: hy_Vc
        integer, dimension(LOW:HIGH, MDIM), intent(IN) :: blkLimits, blkLimitsGC
        integer, intent(IN) :: stage
        end subroutine Hydro_prepBlock
    !!milhoja end
end interface

'''''''''''