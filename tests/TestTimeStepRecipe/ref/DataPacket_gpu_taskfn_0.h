#ifndef DATAPACKET_GPU_TASKFN_0_UNIQUE_IFNDEF_H_
#define DATAPACKET_GPU_TASKFN_0_UNIQUE_IFNDEF_H_

#include <Milhoja.h>
#include <Milhoja_real.h>
#include <Milhoja_DataPacket.h>
#include <climits>

using real = milhoja::Real;
using milhoja::FArray4D;
using milhoja::IntVect;
using milhoja::RealVect;

class DataPacket_gpu_taskfn_0 : public milhoja::DataPacket {
public:
    // constructor
    DataPacket_gpu_taskfn_0(
    real external_Hydro_dt,real external_Hydro_dtOld,int external_Hydro_stage
    );
    // destructor
    ~DataPacket_gpu_taskfn_0(void);

    //helper methods from base DataPacket class.
    std::unique_ptr<milhoja::DataPacket> clone(void) const override;
    DataPacket_gpu_taskfn_0(DataPacket_gpu_taskfn_0&) = delete;
    DataPacket_gpu_taskfn_0(const DataPacket_gpu_taskfn_0&) = delete;
    DataPacket_gpu_taskfn_0(DataPacket_gpu_taskfn_0&& packet) = delete;
    DataPacket_gpu_taskfn_0& operator=(DataPacket_gpu_taskfn_0&) = delete;
    DataPacket_gpu_taskfn_0& operator=(const DataPacket_gpu_taskfn_0&) = delete;
    DataPacket_gpu_taskfn_0& operator=(DataPacket_gpu_taskfn_0&& rhs) = delete;

    // pack and unpack functions from base class.
    void pack(void) override;
    void unpack(void) override;

    // TODO: Streams should be stored inside of an array.

    // DataPacket members are made public so a matching task function can easily access them.
    // Since both files are auto-generated and not maintained by humans, this is fine.
    real _external_Hydro_dt_h;
    real* _external_Hydro_dt_d;
    real _external_Hydro_dtOld_h;
    real* _external_Hydro_dtOld_d;
    int _external_Hydro_stage_h;
    int* _external_Hydro_stage_d;
    int _nTiles_h;
    int* _nTiles_d;
    real* _tile_deltas_d;
    int* _tile_arrayBounds_d;
    int* _tile_interior_d;
    int* _tile_lbound_d;
    int* _tile_lo_d;
    real* _CC_1_d;
    real* _CC_1_p;
    real* _scratch_Hydro_cvol_fake_d;
    real* _scratch_Hydro_fareaX_fake_d;
    real* _scratch_Hydro_fareaY_fake_d;
    real* _scratch_Hydro_fareaZ_fake_d;
    real* _scratch_Hydro_hy_Vc_d;
    real* _scratch_Hydro_hy_flat3d_d;
    real* _scratch_Hydro_hy_flux_d;
    real* _scratch_Hydro_hy_fluxBufX_d;
    real* _scratch_Hydro_hy_fluxBufY_d;
    real* _scratch_Hydro_hy_fluxBufZ_d;
    real* _scratch_Hydro_hy_flx_d;
    real* _scratch_Hydro_hy_fly_d;
    real* _scratch_Hydro_hy_flz_d;
    real* _scratch_Hydro_hy_grav_d;
    real* _scratch_Hydro_hy_rope_d;
    real* _scratch_Hydro_hy_starState_d;
    real* _scratch_Hydro_hy_tmpState_d;
    real* _scratch_Hydro_hy_uMinus_d;
    real* _scratch_Hydro_hy_uPlus_d;
    real* _scratch_Hydro_xCenter_fake_d;
    real* _scratch_Hydro_xLeft_fake_d;
    real* _scratch_Hydro_xRight_fake_d;
    real* _scratch_Hydro_yCenter_fake_d;
    real* _scratch_Hydro_yLeft_fake_d;
    real* _scratch_Hydro_yRight_fake_d;
    real* _scratch_Hydro_zCenter_fake_d;
private:
    static constexpr std::size_t ALIGN_SIZE=1;
    static constexpr std::size_t pad(const std::size_t size) {
        return (((size + ALIGN_SIZE - 1) / ALIGN_SIZE) * ALIGN_SIZE);
    }

    // TODO: Streams should be stored inside of an array. Doing so would simplify the code
    // generation & source code for the stream functions.

    static constexpr std::size_t SIZE_EXTERNAL_HYDRO_DT = sizeof(real);
    static constexpr std::size_t SIZE_EXTERNAL_HYDRO_DTOLD = sizeof(real);
    static constexpr std::size_t SIZE_EXTERNAL_HYDRO_STAGE = sizeof(int);
    static constexpr std::size_t SIZE_NTILES = sizeof(int);
    static constexpr std::size_t SIZE_TILE_DELTAS = MILHOJA_MDIM * sizeof(real);
    static constexpr std::size_t SIZE_TILE_ARRAYBOUNDS = 2 * MILHOJA_MDIM * sizeof(int);
    static constexpr std::size_t SIZE_TILE_INTERIOR = 2 * MILHOJA_MDIM * sizeof(int);
    static constexpr std::size_t SIZE_TILE_LBOUND = MILHOJA_MDIM * sizeof(int);
    static constexpr std::size_t SIZE_TILE_LO = MILHOJA_MDIM * sizeof(int);
    static constexpr std::size_t SIZE_CC_1 = (16 + 2 * 6 * MILHOJA_K1D) * (16 + 2 * 6 * MILHOJA_K2D) * (1 + 2 * 6 * MILHOJA_K3D) * (17 + 1 - 0) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_CVOL_FAKE = (1) * (1) * (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_FAREAX_FAKE = (1) * (1) * (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_FAREAY_FAKE = (1) * (1) * (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_FAREAZ_FAKE = (1) * (1) * (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_VC = (28) * (28) * (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_FLAT3D = (28) * (28) * (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_FLUX = (28) * (28) * (1) * (7) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_FLUXBUFX = (17) * (16) * (1) * (5) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_FLUXBUFY = (16) * (17) * (1) * (5) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_FLUXBUFZ = (16) * (16) * (1) * (5) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_FLX = (28) * (28) * (1) * (5) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_FLY = (28) * (28) * (1) * (5) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_FLZ = (28) * (28) * (1) * (5) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_GRAV = (3) * (28) * (28) * (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_ROPE = (28) * (28) * (1) * (7) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_STARSTATE = (28) * (28) * (1) * (18) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_TMPSTATE = (28) * (28) * (1) * (18) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_UMINUS = (28) * (28) * (1) * (7) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_HY_UPLUS = (28) * (28) * (1) * (7) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_XCENTER_FAKE = (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_XLEFT_FAKE = (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_XRIGHT_FAKE = (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_YCENTER_FAKE = (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_YLEFT_FAKE = (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_YRIGHT_FAKE = (1) * sizeof(real);
    static constexpr std::size_t SIZE_SCRATCH_HYDRO_ZCENTER_FAKE = (1) * sizeof(real);
};

#endif

