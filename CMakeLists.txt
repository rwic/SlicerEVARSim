cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(EVARSim)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/EVARSim")
set(EXTENSION_CONTRIBUTORS "Ralph Wickenhoefer (rwGroup)")
set(EXTENSION_DESCRIPTION "Simulation of endovascular Devices")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/rwic/SlicerEVARSim/refs/heads/main/EVARSim/Resources/Icons/EVARSim.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/rwic/SlicerEVARSim/refs/heads/main/EVARSim/Resources/Icons/1.jpeg")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(Test)
add_subdirectory(EVARSim)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
