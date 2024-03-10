module DataPacket_gpu_taskfn_0_c2f_mod
   implicit none
   private

   public :: instantiate_gpu_taskfn_0_packet_c
   public :: delete_gpu_taskfn_0_packet_c
   public :: release_gpu_taskfn_0_extra_queue_c

   interface
      function instantiate_gpu_taskfn_0_packet_c( &
         C_external_Hydro_dt, &
         C_external_Hydro_dtOld, &
         C_external_Hydro_stage, &
         C_packet &
      ) result(C_ierr) &
            bind(c, name="instantiate_gpu_taskfn_0_packet_c")
         use iso_c_binding, ONLY: C_PTR
         use milhoja_types_mod, ONLY: MILHOJA_INT, MILHOJA_REAL
         real(MILHOJA_REAL), intent(IN), value :: C_external_Hydro_dt
         real(MILHOJA_REAL), intent(IN), value :: C_external_Hydro_dtOld
         integer(MILHOJA_INT), intent(IN), value :: C_external_Hydro_stage
         type(C_PTR), intent(IN) :: C_packet
         integer(MILHOJA_INT) :: C_ierr
      end function instantiate_gpu_taskfn_0_packet_c

      function delete_gpu_taskfn_0_packet_c(C_packet) result(C_ierr) &
            bind(c, name="delete_gpu_taskfn_0_packet_c")
         use iso_c_binding, ONLY : C_PTR
         use milhoja_types_mod, ONLY : MILHOJA_INT
         type(C_PTR), intent(IN), value :: C_packet
         integer(MILHOJA_INT) :: C_ierr
      end function delete_gpu_taskfn_0_packet_c
   end interface

   interface
      function release_gpu_taskfn_0_extra_queue_c(C_packet, C_id) result(C_ierr) &
            bind(c, name="release_gpu_taskfn_0_extra_queue_c")
         use iso_c_binding, ONLY : C_PTR
         use milhoja_types_mod, ONLY : MILHOJA_INT
         type(C_PTR), intent(IN), value :: C_packet
         integer(MILHOJA_INT), intent(IN), value :: C_id
         integer(MILHOJA_INT) :: C_ierr
      end function release_gpu_taskfn_0_extra_queue_c
   end interface

end module DataPacket_gpu_taskfn_0_c2f_mod

