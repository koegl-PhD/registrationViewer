cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(basic)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/basic")
set(EXTENSION_CATEGORY "Examples")
set(EXTENSION_CONTRIBUTORS "Fryderyk Kögl (MRI (TUM))")
set(EXTENSION_DESCRIPTION "The most basic extension")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/basic.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/basic/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(registrationViewer)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
