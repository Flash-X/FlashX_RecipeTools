

#include <iostream>
#include <Milhoja.h>
#include <Milhoja_real.h>
#include <Milhoja_interface_error_codes.h>

#include "DataPacket_gpu_taskfn_0.h"

#ifndef MILHOJA_OPENACC_OFFLOADING
#error "This file should only be compiled if using OpenACC offloading"
#endif

using milhoja::Real;

extern "C" {
    //----- C DECLARATION OF FORTRAN ROUTINE WITH C-COMPATIBLE INTERFACE
    void gpu_taskfn_0_C2F (
    void* packet_h,
    const int queue1_h,
    const int _nTiles_h,
    const void* _nTiles_d,
    const void* _external_Hydro_dt_d,
    const void* _external_Hydro_dtOld_d,
    const void* _external_Hydro_stage_d,
    const void* _tile_arrayBounds_d,
    const void* _tile_deltas_d,
    const void* _tile_interior_d,
    const void* _tile_lbound_d,
    const void* _tile_lo_d,
    const void* _CC_1_d,
    const void* _scratch_Hydro_cvol_fake_d,
    const void* _scratch_Hydro_fareaX_fake_d,
    const void* _scratch_Hydro_fareaY_fake_d,
    const void* _scratch_Hydro_fareaZ_fake_d,
    const void* _scratch_Hydro_hy_Vc_d,
    const void* _scratch_Hydro_hy_flat3d_d,
    const void* _scratch_Hydro_hy_flux_d,
    const void* _scratch_Hydro_hy_fluxBufX_d,
    const void* _scratch_Hydro_hy_fluxBufY_d,
    const void* _scratch_Hydro_hy_fluxBufZ_d,
    const void* _scratch_Hydro_hy_flx_d,
    const void* _scratch_Hydro_hy_fly_d,
    const void* _scratch_Hydro_hy_flz_d,
    const void* _scratch_Hydro_hy_grav_d,
    const void* _scratch_Hydro_hy_rope_d,
    const void* _scratch_Hydro_hy_starState_d,
    const void* _scratch_Hydro_hy_tmpState_d,
    const void* _scratch_Hydro_hy_uMinus_d,
    const void* _scratch_Hydro_hy_uPlus_d,
    const void* _scratch_Hydro_xCenter_fake_d,
    const void* _scratch_Hydro_xLeft_fake_d,
    const void* _scratch_Hydro_xRight_fake_d,
    const void* _scratch_Hydro_yCenter_fake_d,
    const void* _scratch_Hydro_yLeft_fake_d,
    const void* _scratch_Hydro_yRight_fake_d,
    const void* _scratch_Hydro_zCenter_fake_d
    );

    int instantiate_gpu_taskfn_0_packet_c (
    real external_Hydro_dt,
    real external_Hydro_dtOld,
    int external_Hydro_stage,
    void** packet
    ) {
        if ( packet == nullptr) {
            std::cerr << "[instantiate_gpu_taskfn_0_packet_c] packet is NULL" << std::endl;
            return MILHOJA_ERROR_POINTER_IS_NULL;
        } else if (*packet != nullptr) {
            std::cerr << "[instantiate_gpu_taskfn_0_packet_c] *packet not NULL" << std::endl;
            return MILHOJA_ERROR_POINTER_NOT_NULL;
        }

        try {
            *packet = static_cast<void*>(new DataPacket_gpu_taskfn_0(
            external_Hydro_dt,
            external_Hydro_dtOld,
            external_Hydro_stage
            ));
        } catch (const std::exception& exc) {
            std::cerr << exc.what() << std::endl;
            return MILHOJA_ERROR_UNABLE_TO_CREATE_PACKET;
        } catch (...) {
            std::cerr << "[instantiate_gpu_taskfn_0_packet_c] Unknown error caught" << std::endl;
            return MILHOJA_ERROR_UNABLE_TO_CREATE_PACKET;
        }

        return MILHOJA_SUCCESS;
    }

    int delete_gpu_taskfn_0_packet_c (void* packet) {
        if (packet == nullptr) {
            std::cerr << "[delete_gpu_taskfn_0_packet_c] packet is NULL" << std::endl;
            return MILHOJA_ERROR_POINTER_IS_NULL;
        }
        delete static_cast< DataPacket_gpu_taskfn_0 *>(packet);
        return MILHOJA_SUCCESS;
    }

    int release_gpu_taskfn_0_extra_queue_c (void* packet, const int id) {
        std::cerr << "[release_gpu_taskfn_0_extra_queue_c] Packet does not have extra queues." << std::endl;
        return MILHOJA_ERROR_UNABLE_TO_RELEASE_STREAM;
    }

    //----- C TASK FUNCTION TO BE CALLED BY RUNTIME
    void gpu_taskfn_0_Cpp2C (const int threadIndex, void* dataItem_h) {
        DataPacket_gpu_taskfn_0* packet_h = static_cast<DataPacket_gpu_taskfn_0*>(dataItem_h);
        const int queue1_h = packet_h->asynchronousQueue();
        const int _nTiles_h = packet_h->_nTiles_h;

        void* _nTiles_d = static_cast<void*>( packet_h->_nTiles_d );
        void* _external_Hydro_dt_d = static_cast<void*>( packet_h->_external_Hydro_dt_d );
        void* _external_Hydro_dtOld_d = static_cast<void*>( packet_h->_external_Hydro_dtOld_d );
        void* _external_Hydro_stage_d = static_cast<void*>( packet_h->_external_Hydro_stage_d );
        void* _tile_arrayBounds_d = static_cast<void*>( packet_h->_tile_arrayBounds_d );
        void* _tile_deltas_d = static_cast<void*>( packet_h->_tile_deltas_d );
        void* _tile_interior_d = static_cast<void*>( packet_h->_tile_interior_d );
        void* _tile_lbound_d = static_cast<void*>( packet_h->_tile_lbound_d );
        void* _tile_lo_d = static_cast<void*>( packet_h->_tile_lo_d );
        void* _CC_1_d = static_cast<void*>( packet_h->_CC_1_d );
        void* _scratch_Hydro_cvol_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_cvol_fake_d );
        void* _scratch_Hydro_fareaX_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_fareaX_fake_d );
        void* _scratch_Hydro_fareaY_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_fareaY_fake_d );
        void* _scratch_Hydro_fareaZ_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_fareaZ_fake_d );
        void* _scratch_Hydro_hy_Vc_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_Vc_d );
        void* _scratch_Hydro_hy_flat3d_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_flat3d_d );
        void* _scratch_Hydro_hy_flux_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_flux_d );
        void* _scratch_Hydro_hy_fluxBufX_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_fluxBufX_d );
        void* _scratch_Hydro_hy_fluxBufY_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_fluxBufY_d );
        void* _scratch_Hydro_hy_fluxBufZ_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_fluxBufZ_d );
        void* _scratch_Hydro_hy_flx_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_flx_d );
        void* _scratch_Hydro_hy_fly_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_fly_d );
        void* _scratch_Hydro_hy_flz_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_flz_d );
        void* _scratch_Hydro_hy_grav_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_grav_d );
        void* _scratch_Hydro_hy_rope_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_rope_d );
        void* _scratch_Hydro_hy_starState_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_starState_d );
        void* _scratch_Hydro_hy_tmpState_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_tmpState_d );
        void* _scratch_Hydro_hy_uMinus_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_uMinus_d );
        void* _scratch_Hydro_hy_uPlus_d = static_cast<void*>( packet_h->_scratch_Hydro_hy_uPlus_d );
        void* _scratch_Hydro_xCenter_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_xCenter_fake_d );
        void* _scratch_Hydro_xLeft_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_xLeft_fake_d );
        void* _scratch_Hydro_xRight_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_xRight_fake_d );
        void* _scratch_Hydro_yCenter_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_yCenter_fake_d );
        void* _scratch_Hydro_yLeft_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_yLeft_fake_d );
        void* _scratch_Hydro_yRight_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_yRight_fake_d );
        void* _scratch_Hydro_zCenter_fake_d = static_cast<void*>( packet_h->_scratch_Hydro_zCenter_fake_d );

        // Pass data packet info to C-to-Fortran Reinterpretation Layer
        gpu_taskfn_0_C2F (
        packet_h,
        queue1_h,
        _nTiles_h,
        _nTiles_d,
        _external_Hydro_dt_d,
        _external_Hydro_dtOld_d,
        _external_Hydro_stage_d,
        _tile_arrayBounds_d,
        _tile_deltas_d,
        _tile_interior_d,
        _tile_lbound_d,
        _tile_lo_d,
        _CC_1_d,
        _scratch_Hydro_cvol_fake_d,
        _scratch_Hydro_fareaX_fake_d,
        _scratch_Hydro_fareaY_fake_d,
        _scratch_Hydro_fareaZ_fake_d,
        _scratch_Hydro_hy_Vc_d,
        _scratch_Hydro_hy_flat3d_d,
        _scratch_Hydro_hy_flux_d,
        _scratch_Hydro_hy_fluxBufX_d,
        _scratch_Hydro_hy_fluxBufY_d,
        _scratch_Hydro_hy_fluxBufZ_d,
        _scratch_Hydro_hy_flx_d,
        _scratch_Hydro_hy_fly_d,
        _scratch_Hydro_hy_flz_d,
        _scratch_Hydro_hy_grav_d,
        _scratch_Hydro_hy_rope_d,
        _scratch_Hydro_hy_starState_d,
        _scratch_Hydro_hy_tmpState_d,
        _scratch_Hydro_hy_uMinus_d,
        _scratch_Hydro_hy_uPlus_d,
        _scratch_Hydro_xCenter_fake_d,
        _scratch_Hydro_xLeft_fake_d,
        _scratch_Hydro_xRight_fake_d,
        _scratch_Hydro_yCenter_fake_d,
        _scratch_Hydro_yLeft_fake_d,
        _scratch_Hydro_yRight_fake_d,
        _scratch_Hydro_zCenter_fake_d
        );
    }
}

