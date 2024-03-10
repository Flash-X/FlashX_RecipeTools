!!***h* source/physics/Hydro/HydroMain/Spark/Spark.h
!!
!! This is the internal header file for the Spark Runge-Kutta
!! Hydro unit.
!!
!!***

#include "Simulation.h"
#include "constants.h"

!! PRIMITIVE VARIABLES FOR PENCIL ARRAY
#define HY_DENS 1
#define HY_VELX 2
#define HY_VELY 3
#define HY_VELZ 4
#define HY_PRES 5
#define HY_GAMC 6
#define HY_RHOE 7
#ifdef SPARK_GLM
#define HY_MAGX 8
#define HY_MAGY 9
#define HY_MAGZ 10
#define HY_PSIB 11
#define HY_NUM_VARS 11
#else
#define HY_NUM_VARS 7
#endif

!! CONSERVED/FLUX VARIABLES FOR (M)HD
#define HY_MASS 1
#define HY_XMOM 2
#define HY_YMOM 3
#define HY_ZMOM 4
#define HY_ENER 5
#ifdef SPARK_GLM
#define HY_FMGX 6
#define HY_FMGY 7
#define HY_FMGZ 8
#define HY_FPSI 9
#define HY_NUM_FLUX 9
#else
#define HY_NUM_FLUX 5
#endif

#define NRECON HY_NUM_VARS+NSPECIES+NMASS_SCALARS

#ifdef HY_RK3
#define MAXSTAGE 3
#else     /* default is RK2 */
#define MAXSTAGE 2
#endif
  
