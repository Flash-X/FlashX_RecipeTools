#include <condition_variable>
#include <exception>
#include <iostream>
#include <memory>
#include <mutex>

#include <mpi.h>
#include <openacc.h>

#include <Milhoja_FlashxrTileRaw.h>
#include <Milhoja_Logger.h>
#include <Milhoja_RuntimeBackend.h>
#include <Milhoja_TileFlashxr.h>

#include "DataPacket_newimpl_face_flux_tf.h"

extern "C" void newimpl_face_flux_tf_Cpp2C(int threadIndex, void* dataItem);

namespace {

bool owns_mpi = false;

struct CallbackContext {
    DataPacket_newimpl_face_flux_tf* packet;
    std::mutex mutex;
    std::condition_variable ready;
    bool completed = false;
};

void unpack_packet(void* data) {
    auto* context = static_cast<CallbackContext*>(data);
    context->packet->unpack();
    {
        std::lock_guard<std::mutex> lock(context->mutex);
        context->completed = true;
    }
    context->ready.notify_one();
}

}  // namespace

// Keep the established C ABI used by the shared Fortran comparison driver.
extern "C" int newimpl_face_flux_hostmem_initialize_c() {
    try {
        int mpi_initialized = 0;
        MPI_Initialized(&mpi_initialized);
        if (!mpi_initialized) {
            MPI_Init(nullptr, nullptr);
            owns_mpi = true;
        }
        constexpr std::size_t pool_bytes = 16 * 1024 * 1024;
        milhoja::RuntimeBackend::initialize(1, pool_bytes, pool_bytes);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << std::endl;
        return 1;
    }
}

extern "C" int newimpl_face_flux_hostmem_finalize_c() {
    try {
        milhoja::RuntimeBackend::instance().finalize();
        milhoja::Logger::instance().finalize();
        if (owns_mpi) {
            MPI_Finalize();
            owns_mpi = false;
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << std::endl;
        return 1;
    }
}

extern "C" int run_newimpl_face_flux_hostmem_c(
    milhoja::Real* state,
    milhoja::Real* flux_x,
    milhoja::Real* flux_y,
    int ndim,
    milhoja::Real density_floor,
    milhoja::Real pressure_floor,
    milhoja::Real tiny_state,
    milhoja::Real viscosity,
    milhoja::Real weno_epsilon,
    milhoja::Real flattening_eta,
    int flattening_flag,
    int hybrid_flag,
    int shock_marker_flag,
    milhoja::Real* max_speed,
    int* status,
    int* failed_face
) {
    try {
        DataPacket_newimpl_face_flux_tf packet{
            density_floor,
            flattening_eta,
            flattening_flag,
            hybrid_flag,
            ndim,
            pressure_floor,
            shock_marker_flag,
            tiny_state,
            viscosity,
            weno_epsilon
        };

        FlashxrTileRawPtrs pointers{state, flux_x, flux_y, nullptr};
        FlashxTileRawInts integers{
            8,
            5,
            -2, -2, 1,
            19, 19, 1,
            1, 1, 1,
            16, 16, 1,
            2,
            1,
            1,
            1
        };
        FlashxTileRawReals reals{1.0, 1.0, 1.0};

        std::shared_ptr<milhoja::Tile> tile =
            std::make_shared<milhoja::TileFlashxr>(pointers, integers, reals);
        packet.addTile(std::move(tile));
        packet.pack();

        milhoja::RuntimeBackend& backend = milhoja::RuntimeBackend::instance();
        backend.initiateHostToGpuTransfer(packet);
        newimpl_face_flux_tf_Cpp2C(0, &packet);

        // Generated OpenACC wrappers wait for their queue before returning.
        // Scratch remains device-only, so retrieve the diagnostics explicitly.
        acc_memcpy_from_device(
            max_speed,
            packet._scratch_newimpl_face_flux_max_speed_d,
            sizeof(*max_speed)
        );
        acc_memcpy_from_device(
            status,
            packet._scratch_newimpl_face_flux_status_d,
            sizeof(*status)
        );
        acc_memcpy_from_device(
            failed_face,
            packet._scratch_newimpl_face_flux_failed_face_d,
            4 * sizeof(*failed_face)
        );

        CallbackContext callback{&packet};
        backend.initiateGpuToHostTransfer(
            packet, unpack_packet, static_cast<void*>(&callback)
        );
        {
            std::unique_lock<std::mutex> lock(callback.mutex);
            callback.ready.wait(lock, [&callback]() {
                return callback.completed;
            });
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << std::endl;
        return 1;
    }
}
