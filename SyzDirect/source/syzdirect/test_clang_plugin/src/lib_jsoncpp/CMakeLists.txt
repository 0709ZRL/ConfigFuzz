set (JSONCPP_INCLUDE_DIR /usr/local/include)
set (JSONCPP_LIB_DIR /usr/local/lib)
set (ConfigFuzzSourceCodes
    ConfigParser.cc
    ConfigParser.h
    )

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17")
set(CMAKE_MACOSX_RPATH 0)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# message(STATUS "JSONCPP include dir: ${JSONCPP_INCLUDE_DIR}")
# message(STATUS "JSONCPP lib dir: ${JSONCPP_LIB_DIR}")

# Build libraries.
add_library (ConfigFuzzAnalyzerObj OBJECT ${ConfigFuzzSourceCodes} )
add_library (ConfigFuzzAnalyzer SHARED $<TARGET_OBJECTS:ConfigFuzzAnalyzerObj>)
add_library (ConfigFuzzAnalyzerStatic STATIC $<TARGET_OBJECTS:ConfigFuzzAnalyzerObj>)

add_definitions(-DJSON_HAS_INT64)
add_definitions(-DJSON_HAS_STRING_VIEW)
add_definitions(-DJSON_USE_IMPLICIT_CONVERSIONS=0)

# Build executable.
set (EXECUTABLE_OUTPUT_PATH ${ANALYZER_BINARY_DIR})
link_directories (${ANALYZER_BINARY_DIR}/lib_jsoncpp)
link_directories (${JSONCPP_LIB_DIR})
include_directories (${JSONCPP_INCLUDE_DIR})
add_executable (configFuzzPlugin ${ConfigFuzzSourceCodes})

# target_include_directories (configFuzzPlugin
#     PRIVATE
#     ${JSONCPP_INCLUDE_DIR}
#     )
    
target_link_libraries (configFuzzPlugin 
    LLVMAsmParser 
    LLVMSupport 
    LLVMCore 
    LLVMAnalysis
    LLVMIRReader
    ConfigFuzzAnalyzerStatic
    jsoncpp
    )