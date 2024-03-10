#include "DataPacket_gpu_taskfn_0.h"
#include <cassert>
#include <cstring>
#include <stdexcept>
#include <Milhoja_Grid.h>
#include <Milhoja_RuntimeBackend.h>

std::unique_ptr<milhoja::DataPacket> DataPacket_gpu_taskfn_0::clone(void) const {
    return std::unique_ptr<milhoja::DataPacket>{
        new DataPacket_gpu_taskfn_0 {
            _external_Hydro_dt_h,_external_Hydro_dtOld_h,_external_Hydro_stage_h
        }
    };
}

// Constructor arguments for DataPacket classes are copied by value into non-reference data members.
// Thus, these values are frozen at instantiation.
DataPacket_gpu_taskfn_0::DataPacket_gpu_taskfn_0(
real external_Hydro_dt,real external_Hydro_dtOld,int external_Hydro_stage
)
    :
    milhoja::DataPacket{},
_external_Hydro_dt_h{external_Hydro_dt},
_external_Hydro_dt_d{nullptr},
_external_Hydro_dtOld_h{external_Hydro_dtOld},
_external_Hydro_dtOld_d{nullptr},
_nTiles_h{0},
_nTiles_d{nullptr},
_external_Hydro_stage_h{external_Hydro_stage},
_external_Hydro_stage_d{nullptr},
_tile_deltas_d{nullptr},
_tile_arrayBounds_d{nullptr},
_tile_interior_d{nullptr},
_tile_lbound_d{nullptr},
_tile_lo_d{nullptr},
_CC_1_d{nullptr},
_CC_1_p{nullptr},
_scratch_Hydro_cvol_fake_d{nullptr},
_scratch_Hydro_fareaX_fake_d{nullptr},
_scratch_Hydro_fareaY_fake_d{nullptr},
_scratch_Hydro_fareaZ_fake_d{nullptr},
_scratch_Hydro_hy_Vc_d{nullptr},
_scratch_Hydro_hy_flat3d_d{nullptr},
_scratch_Hydro_hy_flux_d{nullptr},
_scratch_Hydro_hy_fluxBufX_d{nullptr},
_scratch_Hydro_hy_fluxBufY_d{nullptr},
_scratch_Hydro_hy_fluxBufZ_d{nullptr},
_scratch_Hydro_hy_flx_d{nullptr},
_scratch_Hydro_hy_fly_d{nullptr},
_scratch_Hydro_hy_flz_d{nullptr},
_scratch_Hydro_hy_grav_d{nullptr},
_scratch_Hydro_hy_rope_d{nullptr},
_scratch_Hydro_hy_starState_d{nullptr},
_scratch_Hydro_hy_tmpState_d{nullptr},
_scratch_Hydro_hy_uMinus_d{nullptr},
_scratch_Hydro_hy_uPlus_d{nullptr},
_scratch_Hydro_xCenter_fake_d{nullptr},
_scratch_Hydro_xLeft_fake_d{nullptr},
_scratch_Hydro_xRight_fake_d{nullptr},
_scratch_Hydro_yCenter_fake_d{nullptr},
_scratch_Hydro_yLeft_fake_d{nullptr},
_scratch_Hydro_yRight_fake_d{nullptr},
_scratch_Hydro_zCenter_fake_d{nullptr}
    {
}

DataPacket_gpu_taskfn_0::~DataPacket_gpu_taskfn_0(void) {
}


void DataPacket_gpu_taskfn_0::pack(void) {
    using namespace milhoja;
    std::string errMsg = isNull();
    if (errMsg != "")
        throw std::logic_error("[DataPacket_gpu_taskfn_0 pack] " + errMsg);
    else if (tiles_.size() == 0)
        throw std::logic_error("[DataPacket_gpu_taskfn_0 pack] No tiles added.");

    // note: cannot set ntiles in the constructor because tiles_ is not filled yet.
    // Check for overflow first to avoid UB
    // TODO: Should casting be checked here or in base class?
    if (tiles_.size() > INT_MAX)
    	throw std::overflow_error("[DataPacket_gpu_taskfn_0 pack] nTiles was too large for int.");
    _nTiles_h = static_cast<int>(tiles_.size());

    constexpr std::size_t SIZE_CONSTRUCTOR = pad(
    SIZE_EXTERNAL_HYDRO_DT
     + SIZE_EXTERNAL_HYDRO_DTOLD
     + SIZE_NTILES
     + SIZE_EXTERNAL_HYDRO_STAGE
    );
    if (SIZE_CONSTRUCTOR % ALIGN_SIZE != 0)
        throw std::logic_error("[DataPacket_gpu_taskfn_0 pack] SIZE_CONSTRUCTOR padding failure");

    std::size_t SIZE_TILEMETADATA = pad( _nTiles_h * (
    SIZE_TILE_DELTAS
     + SIZE_TILE_ARRAYBOUNDS
     + SIZE_TILE_INTERIOR
     + SIZE_TILE_LBOUND
     + SIZE_TILE_LO
    ));
    if (SIZE_TILEMETADATA % ALIGN_SIZE != 0)
        throw std::logic_error("[DataPacket_gpu_taskfn_0 pack] SIZE_TILEMETADATA padding failure");

    std::size_t SIZE_TILEIN = pad( _nTiles_h * (
    0
    ));
    if (SIZE_TILEIN % ALIGN_SIZE != 0)
        throw std::logic_error("[DataPacket_gpu_taskfn_0 pack] SIZE_TILEIN padding failure");

    std::size_t SIZE_TILEINOUT = pad( _nTiles_h * (
    SIZE_CC_1
    ));
    if (SIZE_TILEINOUT % ALIGN_SIZE != 0)
        throw std::logic_error("[DataPacket_gpu_taskfn_0 pack] SIZE_TILEINOUT padding failure");

    std::size_t SIZE_TILEOUT = pad( _nTiles_h * (
    0
    ));
    if (SIZE_TILEOUT % ALIGN_SIZE != 0)
        throw std::logic_error("[DataPacket_gpu_taskfn_0 pack] SIZE_TILEOUT padding failure");

    std::size_t SIZE_TILESCRATCH = pad( _nTiles_h * (
    SIZE_SCRATCH_HYDRO_CVOL_FAKE
     + SIZE_SCRATCH_HYDRO_FAREAX_FAKE
     + SIZE_SCRATCH_HYDRO_FAREAY_FAKE
     + SIZE_SCRATCH_HYDRO_FAREAZ_FAKE
     + SIZE_SCRATCH_HYDRO_HY_VC
     + SIZE_SCRATCH_HYDRO_HY_FLAT3D
     + SIZE_SCRATCH_HYDRO_HY_FLUX
     + SIZE_SCRATCH_HYDRO_HY_FLUXBUFX
     + SIZE_SCRATCH_HYDRO_HY_FLUXBUFY
     + SIZE_SCRATCH_HYDRO_HY_FLUXBUFZ
     + SIZE_SCRATCH_HYDRO_HY_FLX
     + SIZE_SCRATCH_HYDRO_HY_FLY
     + SIZE_SCRATCH_HYDRO_HY_FLZ
     + SIZE_SCRATCH_HYDRO_HY_GRAV
     + SIZE_SCRATCH_HYDRO_HY_ROPE
     + SIZE_SCRATCH_HYDRO_HY_STARSTATE
     + SIZE_SCRATCH_HYDRO_HY_TMPSTATE
     + SIZE_SCRATCH_HYDRO_HY_UMINUS
     + SIZE_SCRATCH_HYDRO_HY_UPLUS
     + SIZE_SCRATCH_HYDRO_XCENTER_FAKE
     + SIZE_SCRATCH_HYDRO_XLEFT_FAKE
     + SIZE_SCRATCH_HYDRO_XRIGHT_FAKE
     + SIZE_SCRATCH_HYDRO_YCENTER_FAKE
     + SIZE_SCRATCH_HYDRO_YLEFT_FAKE
     + SIZE_SCRATCH_HYDRO_YRIGHT_FAKE
     + SIZE_SCRATCH_HYDRO_ZCENTER_FAKE
    ));
    if (SIZE_TILESCRATCH % ALIGN_SIZE != 0)
        throw std::logic_error("[DataPacket_gpu_taskfn_0 pack] SIZE_TILESCRATCH padding failure");

    nCopyToGpuBytes_ = SIZE_CONSTRUCTOR + SIZE_TILEMETADATA + SIZE_TILEIN + SIZE_TILEINOUT;
    nReturnToHostBytes_ = SIZE_TILEINOUT + SIZE_TILEOUT;
    std::size_t nBytesPerPacket = SIZE_CONSTRUCTOR + SIZE_TILEMETADATA + SIZE_TILEIN + SIZE_TILEINOUT + SIZE_TILEOUT;
    RuntimeBackend::instance().requestGpuMemory(nBytesPerPacket, &packet_p_, nBytesPerPacket + SIZE_TILESCRATCH, &packet_d_);

    // pointer determination phase
    static_assert(sizeof(char) == 1);
    char* ptr_d = static_cast<char*>(packet_d_);

    _scratch_Hydro_cvol_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_CVOL_FAKE;

    _scratch_Hydro_fareaX_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_FAREAX_FAKE;

    _scratch_Hydro_fareaY_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_FAREAY_FAKE;

    _scratch_Hydro_fareaZ_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_FAREAZ_FAKE;

    _scratch_Hydro_hy_Vc_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_VC;

    _scratch_Hydro_hy_flat3d_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_FLAT3D;

    _scratch_Hydro_hy_flux_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_FLUX;

    _scratch_Hydro_hy_fluxBufX_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_FLUXBUFX;

    _scratch_Hydro_hy_fluxBufY_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_FLUXBUFY;

    _scratch_Hydro_hy_fluxBufZ_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_FLUXBUFZ;

    _scratch_Hydro_hy_flx_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_FLX;

    _scratch_Hydro_hy_fly_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_FLY;

    _scratch_Hydro_hy_flz_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_FLZ;

    _scratch_Hydro_hy_grav_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_GRAV;

    _scratch_Hydro_hy_rope_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_ROPE;

    _scratch_Hydro_hy_starState_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_STARSTATE;

    _scratch_Hydro_hy_tmpState_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_TMPSTATE;

    _scratch_Hydro_hy_uMinus_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_UMINUS;

    _scratch_Hydro_hy_uPlus_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_HY_UPLUS;

    _scratch_Hydro_xCenter_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_XCENTER_FAKE;

    _scratch_Hydro_xLeft_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_XLEFT_FAKE;

    _scratch_Hydro_xRight_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_XRIGHT_FAKE;

    _scratch_Hydro_yCenter_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_YCENTER_FAKE;

    _scratch_Hydro_yLeft_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_YLEFT_FAKE;

    _scratch_Hydro_yRight_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_YRIGHT_FAKE;

    _scratch_Hydro_zCenter_fake_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_d += _nTiles_h * SIZE_SCRATCH_HYDRO_ZCENTER_FAKE;
    copyInStart_p_ = static_cast<char*>(packet_p_);
    copyInStart_d_ = static_cast<char*>(packet_d_) + SIZE_TILESCRATCH;
    char* ptr_p = copyInStart_p_;
    ptr_d = copyInStart_d_;

    real* _external_Hydro_dt_p = static_cast<real*>( static_cast<void*>(ptr_p) );
    _external_Hydro_dt_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_p+=SIZE_EXTERNAL_HYDRO_DT;
    ptr_d+=SIZE_EXTERNAL_HYDRO_DT;

    real* _external_Hydro_dtOld_p = static_cast<real*>( static_cast<void*>(ptr_p) );
    _external_Hydro_dtOld_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_p+=SIZE_EXTERNAL_HYDRO_DTOLD;
    ptr_d+=SIZE_EXTERNAL_HYDRO_DTOLD;

    int* _nTiles_p = static_cast<int*>( static_cast<void*>(ptr_p) );
    _nTiles_d = static_cast<int*>( static_cast<void*>(ptr_d) );
    ptr_p+=SIZE_NTILES;
    ptr_d+=SIZE_NTILES;

    int* _external_Hydro_stage_p = static_cast<int*>( static_cast<void*>(ptr_p) );
    _external_Hydro_stage_d = static_cast<int*>( static_cast<void*>(ptr_d) );
    ptr_p+=SIZE_EXTERNAL_HYDRO_STAGE;
    ptr_d+=SIZE_EXTERNAL_HYDRO_STAGE;
    ptr_p = copyInStart_p_ + SIZE_CONSTRUCTOR;
    ptr_d = copyInStart_d_ + SIZE_CONSTRUCTOR;
    real* _tile_deltas_p = static_cast<real*>( static_cast<void*>(ptr_p) );
    _tile_deltas_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_p+=_nTiles_h * SIZE_TILE_DELTAS;
    ptr_d+=_nTiles_h * SIZE_TILE_DELTAS;

    int* _tile_arrayBounds_p = static_cast<int*>( static_cast<void*>(ptr_p) );
    _tile_arrayBounds_d = static_cast<int*>( static_cast<void*>(ptr_d) );
    ptr_p+=_nTiles_h * SIZE_TILE_ARRAYBOUNDS;
    ptr_d+=_nTiles_h * SIZE_TILE_ARRAYBOUNDS;

    int* _tile_interior_p = static_cast<int*>( static_cast<void*>(ptr_p) );
    _tile_interior_d = static_cast<int*>( static_cast<void*>(ptr_d) );
    ptr_p+=_nTiles_h * SIZE_TILE_INTERIOR;
    ptr_d+=_nTiles_h * SIZE_TILE_INTERIOR;

    int* _tile_lbound_p = static_cast<int*>( static_cast<void*>(ptr_p) );
    _tile_lbound_d = static_cast<int*>( static_cast<void*>(ptr_d) );
    ptr_p+=_nTiles_h * SIZE_TILE_LBOUND;
    ptr_d+=_nTiles_h * SIZE_TILE_LBOUND;

    int* _tile_lo_p = static_cast<int*>( static_cast<void*>(ptr_p) );
    _tile_lo_d = static_cast<int*>( static_cast<void*>(ptr_d) );
    ptr_p+=_nTiles_h * SIZE_TILE_LO;
    ptr_d+=_nTiles_h * SIZE_TILE_LO;
    ptr_p = copyInStart_p_ + SIZE_CONSTRUCTOR + SIZE_TILEMETADATA;
    ptr_d = copyInStart_d_ + SIZE_CONSTRUCTOR + SIZE_TILEMETADATA;
    copyInOutStart_p_ = copyInStart_p_ + SIZE_CONSTRUCTOR + SIZE_TILEMETADATA + SIZE_TILEIN;
    copyInOutStart_d_ = copyInStart_d_ + SIZE_CONSTRUCTOR + SIZE_TILEMETADATA + SIZE_TILEIN;
    ptr_p = copyInOutStart_p_;
    ptr_d = copyInOutStart_d_;
    _CC_1_p = static_cast<real*>( static_cast<void*>(ptr_p) );
    _CC_1_d = static_cast<real*>( static_cast<void*>(ptr_d) );
    ptr_p+=_nTiles_h * SIZE_CC_1;
    ptr_d+=_nTiles_h * SIZE_CC_1;
    char* copyOutStart_p_ = copyInOutStart_p_ + SIZE_TILEINOUT;
    char* copyOutStart_d_ = copyInOutStart_d_ + SIZE_TILEINOUT;
    //memcopy phase
    std::memcpy(_external_Hydro_dt_p, static_cast<void*>(&_external_Hydro_dt_h), SIZE_EXTERNAL_HYDRO_DT);
    std::memcpy(_external_Hydro_dtOld_p, static_cast<void*>(&_external_Hydro_dtOld_h), SIZE_EXTERNAL_HYDRO_DTOLD);
    std::memcpy(_nTiles_p, static_cast<void*>(&_nTiles_h), SIZE_NTILES);
    std::memcpy(_external_Hydro_stage_p, static_cast<void*>(&_external_Hydro_stage_h), SIZE_EXTERNAL_HYDRO_STAGE);
    char* char_ptr;
    for (auto n = 0; n < _nTiles_h; n++) {
        Tile* tileDesc_h = tiles_[n].get();
        if (tileDesc_h == nullptr) throw std::runtime_error("[DataPacket_gpu_taskfn_0 pack] Bad tiledesc.");
        const auto deltas = tileDesc_h->deltas();
        const auto lbound = tileDesc_h->loGC();
        const auto lo = tileDesc_h->lo();
        real _tile_deltas_h[MILHOJA_MDIM] = { deltas.I(), deltas.J(), deltas.K() };
        char_ptr = static_cast<char*>(static_cast<void*>(_tile_deltas_p)) + n * SIZE_TILE_DELTAS;
        std::memcpy(static_cast<void*>(char_ptr), static_cast<void*>(_tile_deltas_h), SIZE_TILE_DELTAS);

        int _tile_arrayBounds_h[MILHOJA_MDIM * 2] = {tileDesc_h->loGC().I()+1,tileDesc_h->hiGC().I()+1, tileDesc_h->loGC().J()+1,tileDesc_h->hiGC().J()+1, tileDesc_h->loGC().K()+1,tileDesc_h->hiGC().K()+1 };
        char_ptr = static_cast<char*>(static_cast<void*>(_tile_arrayBounds_p)) + n * SIZE_TILE_ARRAYBOUNDS;
        std::memcpy(static_cast<void*>(char_ptr), static_cast<void*>(_tile_arrayBounds_h), SIZE_TILE_ARRAYBOUNDS);

        int _tile_interior_h[MILHOJA_MDIM * 2] = {tileDesc_h->lo().I()+1,tileDesc_h->hi().I()+1, tileDesc_h->lo().J()+1,tileDesc_h->hi().J()+1, tileDesc_h->lo().K()+1,tileDesc_h->hi().K()+1 };
        char_ptr = static_cast<char*>(static_cast<void*>(_tile_interior_p)) + n * SIZE_TILE_INTERIOR;
        std::memcpy(static_cast<void*>(char_ptr), static_cast<void*>(_tile_interior_h), SIZE_TILE_INTERIOR);

        int _tile_lbound_h[MILHOJA_MDIM] = { lbound.I()+1, lbound.J()+1, lbound.K()+1 };
        char_ptr = static_cast<char*>(static_cast<void*>(_tile_lbound_p)) + n * SIZE_TILE_LBOUND;
        std::memcpy(static_cast<void*>(char_ptr), static_cast<void*>(_tile_lbound_h), SIZE_TILE_LBOUND);

        int _tile_lo_h[MILHOJA_MDIM] = { lo.I()+1, lo.J()+1, lo.K()+1 };
        char_ptr = static_cast<char*>(static_cast<void*>(_tile_lo_p)) + n * SIZE_TILE_LO;
        std::memcpy(static_cast<void*>(char_ptr), static_cast<void*>(_tile_lo_h), SIZE_TILE_LO);
        real* CC_1_d = tileDesc_h->dataPtr();
        constexpr std::size_t offset_CC_1 = (16 + 2 * 6 * MILHOJA_K1D) * (16 + 2 * 6 * MILHOJA_K2D) * (1 + 2 * 6 * MILHOJA_K3D) * static_cast<std::size_t>(0);
        constexpr std::size_t nBytes_CC_1 = (16 + 2 * 6 * MILHOJA_K1D) * (16 + 2 * 6 * MILHOJA_K2D) * (1 + 2 * 6 * MILHOJA_K3D) * ( 17 - 0 + 1 ) * sizeof(real);
        char_ptr = static_cast<char*>( static_cast<void*>(_CC_1_p) ) + n * SIZE_CC_1;
        std::memcpy(static_cast<void*>(char_ptr), static_cast<void*>(CC_1_d + offset_CC_1), nBytes_CC_1);
    }

    stream_ = RuntimeBackend::instance().requestStream(true);
    if (!stream_.isValid())
        throw std::runtime_error("[DataPacket_gpu_taskfn_0 pack] Unable to acquire stream 1.");
}

void DataPacket_gpu_taskfn_0::unpack(void) {
    using namespace milhoja;
    if (tiles_.size() <= 0)
        throw std::logic_error("[DataPacket_gpu_taskfn_0 unpack] Empty data packet.");
    if (!stream_.isValid())
        throw std::logic_error("[DataPacket_gpu_taskfn_0 unpack] Stream not acquired.");
    RuntimeBackend::instance().releaseStream(stream_);
    assert(!stream_.isValid());
    for (auto n = 0; n < _nTiles_h; ++n) {
        Tile* tileDesc_h = tiles_[n].get();
        real* CC_1_data_h = tileDesc_h->dataPtr();
        real* CC_1_data_p = static_cast<real*>( static_cast<void*>( static_cast<char*>( static_cast<void*>( _CC_1_p ) ) + n * SIZE_CC_1 ) );
        constexpr std::size_t offset_CC_1 = (16 + 2 * 6 * MILHOJA_K1D) * (16 + 2 * 6 * MILHOJA_K2D) * (1 + 2 * 6 * MILHOJA_K3D) * static_cast<std::size_t>(0);
        real*        start_h_CC_1 = CC_1_data_h + offset_CC_1;
        const real*  start_p_CC_1 = CC_1_data_p + offset_CC_1;
        constexpr std::size_t nBytes_CC_1 = (16 + 2 * 6 * MILHOJA_K1D) * (16 + 2 * 6 * MILHOJA_K2D) * (1 + 2 * 6 * MILHOJA_K3D) * ( 17 - 0 + 1 ) * sizeof(real);
        std::memcpy(static_cast<void*>(start_h_CC_1), static_cast<const void*>(start_p_CC_1), nBytes_CC_1);
    }
}

