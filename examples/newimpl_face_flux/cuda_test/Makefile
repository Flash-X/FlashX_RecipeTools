MILHOJA_PREFIX ?= ../../../../Milhoja/2D-cuda
LAYOUT ?= variable-last
GROUPING ?= fully_fused
PYTHON ?= python3
RECIPE_PYTHONPATH ?= ../../../src:$(abspath $(MILHOJA_PREFIX)/../tools/milhoja_pypkg/src)
NEWIMPL_SOURCE ?= ../../../../Flash-X/source/physics/Hydro/HydroMain/Spark/NewImpl

FC = mpif90
CXX = mpicxx
MPICXX = mpicxx
LINKER = mpif90

OFFLOAD_FLAGS ?= -acc=gpu -gpu=ccnative,cuda13.1,ptxinfo -Minfo=accel
MIXED_LINK_FLAGS ?= -cudalib -lstdc++
RUNNER ?= timeout 90s env OMPI_MCA_coll_ucc_enable=0 \
          OMPI_MCA_coll_hcoll_enable=0 OMPI_MCA_pml=ob1 \
          OMPI_MCA_btl=self UCX_MODULES=^cuda mpirun -np 1
MPI_CXXFLAGS = $(shell $(MPICXX) --showme:compile)

ifeq ($(GROUPING),fully_fused)
else ifeq ($(GROUPING),flattening_then_directional)
else ifeq ($(GROUPING),flattening_reconstruction_solve)
else
$(error Unsupported GROUPING '$(GROUPING)')
endif

GENERATED ?= ../generated/cuda-$(LAYOUT)-$(GROUPING)
BUILD ?= ../build/cuda-$(LAYOUT)-$(GROUPING)

ifeq ($(LAYOUT),variable-last)
LAYOUT_FLAGS :=
else ifeq ($(LAYOUT),variable-first)
LAYOUT_FLAGS := -DNEWIMPL_VARIABLE_FIRST
else
$(error Unsupported LAYOUT '$(LAYOUT)'; use variable-last or variable-first)
endif

TARGET := $(BUILD)/test_newimpl_face_flux_cuda
STAMP := $(GENERATED)/.generated
TEST_SOURCE := ../runtime_test/test_newimpl_face_flux_hostmem.F90

FFLAGS := -Mpreprocess -Mrecursive -i4 -r8 -traceback \
          $(OFFLOAD_FLAGS) $(LAYOUT_FLAGS) -DNEWIMPL_CUDA_OPENACC \
          -I$(MILHOJA_PREFIX)/include -I$(BUILD) -module $(BUILD)
CXXFLAGS := -std=c++17 -O2 $(OFFLOAD_FLAGS) $(LAYOUT_FLAGS) \
            -I$(MILHOJA_PREFIX)/include -I$(GENERATED)

OBJECTS := \
  $(BUILD)/newimpl_face_flux_milhoja.o \
  $(BUILD)/newimpl_face_flux_adapter_mod.o \
  $(BUILD)/newimpl_face_flux_tf_mod.o \
  $(BUILD)/newimpl_face_flux_tf_C2F.o \
  $(BUILD)/DataPacket_newimpl_face_flux_tf.o \
  $(BUILD)/newimpl_face_flux_tf.o \
  $(BUILD)/newimpl_face_flux_cuda_bridge.o \
  $(BUILD)/test_newimpl_face_flux_cuda.o

.PHONY: all generate regenerate run run-matrix clean

all: generate $(TARGET)

generate: $(STAMP)

$(STAMP): ../generate_taskfunction.py ../grouping_config.py \
          ../newimpl_face_flux.boundaries.json
	PYTHONPATH=$(RECIPE_PYTHONPATH) $(PYTHON) ../generate_taskfunction.py \
	  $(NEWIMPL_SOURCE) $(MILHOJA_PREFIX) $(GENERATED) \
	  --execution cuda-openacc --layout $(LAYOUT) \
	  --grouping $(GROUPING) --overwrite
	touch $(STAMP)

regenerate:
	PYTHONPATH=$(RECIPE_PYTHONPATH) $(PYTHON) ../generate_taskfunction.py \
	  $(NEWIMPL_SOURCE) $(MILHOJA_PREFIX) $(GENERATED) \
	  --execution cuda-openacc --layout $(LAYOUT) \
	  --grouping $(GROUPING) --overwrite
	touch $(STAMP)

run: $(TARGET)
	$(RUNNER) $(TARGET)

run-matrix:
	$(MAKE) run LAYOUT=variable-last GROUPING=fully_fused
	$(MAKE) run LAYOUT=variable-last GROUPING=flattening_then_directional
	$(MAKE) run LAYOUT=variable-last GROUPING=flattening_reconstruction_solve
	$(MAKE) run LAYOUT=variable-first GROUPING=fully_fused
	$(MAKE) run LAYOUT=variable-first GROUPING=flattening_then_directional
	$(MAKE) run LAYOUT=variable-first GROUPING=flattening_reconstruction_solve

$(GENERATED)/newimpl_face_flux_milhoja.F90 \
$(GENERATED)/newimpl_face_flux_adapter_mod.F90 \
$(GENERATED)/newimpl_face_flux_tf_mod.F90 \
$(GENERATED)/newimpl_face_flux_tf_C2F.F90 \
$(GENERATED)/DataPacket_newimpl_face_flux_tf.cxx \
$(GENERATED)/newimpl_face_flux_tf.cxx: $(STAMP)

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/newimpl_face_flux_milhoja.o: $(GENERATED)/newimpl_face_flux_milhoja.F90 | $(BUILD)
	$(FC) $(FFLAGS) -c $< -o $@

$(BUILD)/newimpl_face_flux_adapter_mod.o: $(GENERATED)/newimpl_face_flux_adapter_mod.F90 $(BUILD)/newimpl_face_flux_milhoja.o
	$(FC) $(FFLAGS) -c $< -o $@

$(BUILD)/newimpl_face_flux_tf_mod.o: $(GENERATED)/newimpl_face_flux_tf_mod.F90 $(BUILD)/newimpl_face_flux_adapter_mod.o
	$(FC) $(FFLAGS) -c $< -o $@

$(BUILD)/newimpl_face_flux_tf_C2F.o: $(GENERATED)/newimpl_face_flux_tf_C2F.F90 $(BUILD)/newimpl_face_flux_tf_mod.o
	$(FC) $(FFLAGS) -c $< -o $@

$(BUILD)/DataPacket_newimpl_face_flux_tf.o: $(GENERATED)/DataPacket_newimpl_face_flux_tf.cxx | $(BUILD)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(BUILD)/newimpl_face_flux_tf.o: $(GENERATED)/newimpl_face_flux_tf.cxx | $(BUILD)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(BUILD)/newimpl_face_flux_cuda_bridge.o: newimpl_face_flux_cuda_bridge.cpp | $(BUILD)
	$(CXX) $(MPI_CXXFLAGS) $(CXXFLAGS) -c $< -o $@

$(BUILD)/test_newimpl_face_flux_cuda.o: $(TEST_SOURCE) $(BUILD)/newimpl_face_flux_adapter_mod.o
	$(FC) $(FFLAGS) -c $< -o $@

$(TARGET): $(OBJECTS)
	$(LINKER) $(OBJECTS) $(MILHOJA_PREFIX)/lib/libmilhoja.a \
	  $(OFFLOAD_FLAGS) $(MIXED_LINK_FLAGS) -lpthread -o $@

clean:
	rm -f $(BUILD)/*.o $(BUILD)/*.mod $(TARGET)
