MILHOJA_PREFIX ?= /Users/adubey/ORCHA/Milhoja/2D-hostmem
LAYOUT ?= variable-last
FC = gfortran
CXX = c++
MPICXX = mpicxx
LINKER = mpifort
CXX_RUNTIME ?= -lc++
MPI_CXXFLAGS = $(shell $(MPICXX) --showme:compile)

ifeq ($(LAYOUT),variable-last)
GENERATED ?= ../generated/taskfunction
BUILD ?= ../build/runtime-variable-last
LAYOUT_FFLAGS :=
else ifeq ($(LAYOUT),variable-first)
GENERATED ?= ../generated/taskfunction_variable_first
BUILD ?= ../build/runtime-variable-first
LAYOUT_FFLAGS := -DNEWIMPL_VARIABLE_FIRST
else
$(error Unsupported LAYOUT '$(LAYOUT)'; use variable-last or variable-first)
endif

TARGET := $(BUILD)/test_newimpl_face_flux_hostmem

FFLAGS := -cpp -std=f2008 -Wall -Wextra -fcheck=all \
          $(LAYOUT_FFLAGS) \
          -I$(MILHOJA_PREFIX)/include -I$(BUILD) -J$(BUILD)
CXXFLAGS := -std=c++17 -Wall -Wextra \
            -I$(MILHOJA_PREFIX)/include -I$(GENERATED)

OBJECTS := \
  $(BUILD)/newimpl_face_flux_milhoja.o \
  $(BUILD)/newimpl_face_flux_adapter_mod.o \
  $(BUILD)/newimpl_face_flux_tf_mod.o \
  $(BUILD)/newimpl_face_flux_tf_C2F.o \
  $(BUILD)/DataPacket_newimpl_face_flux_tf.o \
  $(BUILD)/newimpl_face_flux_tf.o \
  $(BUILD)/newimpl_face_flux_hostmem_bridge.o \
  $(BUILD)/test_newimpl_face_flux_hostmem.o

.PHONY: all run clean

all: $(TARGET)

run: $(TARGET)
	$(TARGET)

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

$(BUILD)/newimpl_face_flux_hostmem_bridge.o: newimpl_face_flux_hostmem_bridge.cpp | $(BUILD)
	$(CXX) $(MPI_CXXFLAGS) $(CXXFLAGS) -c $< -o $@

$(BUILD)/test_newimpl_face_flux_hostmem.o: test_newimpl_face_flux_hostmem.F90 $(BUILD)/newimpl_face_flux_adapter_mod.o
	$(FC) $(FFLAGS) -c $< -o $@

$(TARGET): $(OBJECTS)
	$(LINKER) $(OBJECTS) $(MILHOJA_PREFIX)/lib/libmilhoja.a \
	  $(CXX_RUNTIME) -lpthread -o $@

clean:
	rm -f $(BUILD)/*.o $(BUILD)/*.mod $(TARGET)
