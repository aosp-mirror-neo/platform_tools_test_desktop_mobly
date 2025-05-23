# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Lists of VESA Compliance Tests grouped by UCD-500 API."""

from chromiumos.test.lab.api.passport import video_tester_service_pb2 as vts
from display.utils import compliance_tests_manager


# The long lines are the test case descriptions from the VESA standard.
# We disable the lint for this to keep the descriptions more readable.
# pylint: disable=line-too-long

AUDIO_TEST = compliance_tests_manager.TestGroup.from_list(
    group_id=vts.ComplianceTestGroup.GROUP_AUDIO_TEST,
    name="Audio Test",
    test_list=[
        (3, "audio", "Validate audio signal frequency and glitch-free audio reproduction"),
    ]
)

PIXEL_LEVEL_VIDEO_TEST = compliance_tests_manager.TestGroup.from_list(
    group_id=vts.ComplianceTestGroup.GROUP_PIXEL_LEVEL_VIDEO_TEST,
    name="Pixel Level Video Test",
    test_list=[
        (2, "pixel", "Compare video frame sequence with a single reference"),
    ]
)

CRC_BASED_VIDEO_TEST_SET = compliance_tests_manager.TestGroup.from_list(
    group_id=vts.ComplianceTestGroup.GROUP_CRC_BASED_VIDEO_TEST,
    name="CRC based Video Test Set",
    test_list=[
        (0, "CRC_0", "CRC based single reference frame video test"),
        (1, "CRC_1", "CRC based single frame video stability test"),
        (2, "CRC_2", "CRC based sequence of reference frames video test"),
        (3, "CRC_3", "CRC based continuous sequence of reference frames video test"),
    ]
)

LINK_TEST_SET = compliance_tests_manager.TestGroup.from_list(
    group_id=vts.ComplianceTestGroup.GROUP_LINK_TEST,
    name="Link Test Set",
    test_list=[
        (0, "LT", "Link Training at All Supported Lane Counts and Link Rates"),
    ]
)

DP_1_4_LL_CTS = compliance_tests_manager.TestGroup.from_list(
    group_id=vts.ComplianceTestGroup.GROUP_DISPLAYPORT_1_4_LINK_LAYER_CTS,
    name="DP 1.4 Link Layer CTS",
    test_list=[
        (0, "4.2.1.1", "Source DUT Retry on No-Reply During AUX Read after HPD Plug Event (3200us)"),
        (1, "4.2.1.2", "Source Retry on Invalid Reply During AUX Read after HPD Plug Event"),
        (2, "4.2.1.3", "Source Device HPD Event Pulse Length Test"),
        (3, "4.2.1.4", "Source Device IRQ_HPD Pulse Length Test"),
        (4, "4.2.1.5", "Source Device Inactive HPD"),
        (5, "4.2.2.1", "DPCD Receiver Capability and EDID Read upon HPD Plug Event"),
        (6, "4.2.2.2", "DPCD Receiver Capability Read upon HPD Plug Event"),
        (7, "4.2.2.3", "EDID Read"),
        (8, "4.2.2.4", "EDID Read Failure #1: I2C-Over-AUX NACK"),
        (9, "4.2.2.5", "EDID Read Failure #2: I2C-Over-AUX DEFER"),
        (10, "4.2.2.6", "EDID Corruption Detection"),
        (11, "4.2.2.7", "Branch Device Detection upon HPD Plug Event"),
        (12, "4.2.2.8", "EDID Read on IRQ HPD Event after Branch Device Detection"),
        (13, "4.2.2.9", "E-DDC Four Block EDID Read"),
        (14, "4.2.2.10", "Link Status-Adjust Request AUX read interval during Link Training"),
        (15, "4.3.1.1", "Successful LT at All Supported Lane Counts and Link Speeds"),
        (16, "4.3.1.2", "Successful Link Training Upon HPD Plug Event"),
        (17, "4.3.1.3", "Successful LT with Request of Higher Differential Voltage Swing During Clock Recovery Sequence"),
        (18, "4.3.1.4", "Successful LT to a Lower Link Rate #1: Iterate at Max Voltage Swing"),
        (19, "4.3.1.5", "Successful LT to a Lower Link Rate #2: Iterate at Minimum Voltage Swing"),
        (20, "4.3.1.6", "Successful LT with Request of a Higher Pre-emphasis Setting During Channel Equalization Sequence"),
        (21, "4.3.1.7", "Successful LT at Lower Link Rate Due to Loss of Symbol Lock During Channel Equalization Sequence"),
        (22, "4.3.1.8", "Unsuccessful LT at Lower Link Rate #1: Iterate at Max Voltage Swing"),
        (23, "4.3.1.9", "Unsuccessful LT at Lower Link Rate #2: Iterate at Minimum Voltage Swing"),
        (24, "4.3.1.10", "Unsuccessful LT due to Failure in Channel Equalization Sequence [loop count > 5]"),
        (25, "4.3.1.11", "Successful LT with Simultaneous Request for Differential Voltage Swing and Pre-emphasis during Clock Recovery Sequence"),
        (26, "4.3.1.12", "Source Device Link Training CR Fallback Test"),
        (27, "4.3.1.13", "Source Device Link Training EQ Fallback Test"),
        (28, "4.3.2.1", "Successful Link Re-training After IRQ HPD Pulse Due to Loss of Symbol Lock"),
        (29, "4.3.2.2", "Successful Link Re-training After IRQ HPD Pulse Due to Loss of Clock Recovery Lock"),
        (30, "4.3.2.3", "Successful Link Re-training After IRQ HPD Pulse Due to Loss of Inter-lane Alignment Lock"),
        (31, "4.3.2.4", "Handling of IRQ HPD Pulse with No Error Status Bits Set"),
        (32, "4.3.2.5", "Lane Count Reduction"),
        (33, "4.3.3.1", "Video Time Stamp Generation"),
        (34, "4.4.1.1", "Data Packing and Steering"),
        (35, "4.4.1.2", "Main Stream Data Packing and Stuffing - Least Packed TU"),
        (36, "4.4.1.3", "Main Stream Data Packing and Stuffing - Most Packed TU"),
        (37, "4.4.2", "Main Video Stream Format Change Handling"),
        (38, "4.4.3", "Power Management"),
        (39, "4.4.4.2", "Audio Stream Header Synchronization"),
        (40, "4.4.4.3", "Audio Time Stamp Generation"),
        (41, "4.4.4.4", "Audio InfoFrame Packet"),
        (42, "4.4.4.5", "Audio Stream Transmission"),
        (43, "4.4.4.6", "Audio Start Sequence"),
        (44, "4.5.1.1", "FEC enable verification for all supported Lane count and Link Speed"),
        (45, "4.5.1.2", "FEC ready verification for non FEC capable sink"),
    ]
)

DP_1_4_DSC_LL_CTS = compliance_tests_manager.TestGroup.from_list(
    group_id=vts.ComplianceTestGroup.GROUP_DISPLAYPORT_1_4_DSC_LINK_LAYER_CTS,
    name="DP 1.4 DSC Link Layer CTS",
    test_list=[
        (0, "4.6.1.1", "DSC enable sequence verification"),
        (1, "4.6.1.2", "DSC PPS block prediction flag verification"),
        (2, "4.6.1.3", "DSC PPS convert RGB flag verification"),
        (3, "4.6.1.4", "DSC PPS YCbCr 4:4:4 convert RGB=0 flag verification"),
        (4, "4.6.1.5", "DSC PPS Simple 4:2:2 flag verification"),
        (5, "4.6.1.6", "DSC PPS Native 4:2:2 flag verification"),
        (6, "4.6.1.7", "DSC PPS Native 4:2:0 flag verification"),
        (7, "4.6.1.8", "DSC PPS convert RGB flag verification for DSC Algorithm Revision 1.1"),
        (8, "4.6.1.9", "DSC PPS (YCbCr 4:4:4 convert RGB = 0) flag verification for DSC Algorithm Revision 1.1"),
    ]
)

DP_1_4_DISPLAYID_CTS_SOURCE_TEST_SET = compliance_tests_manager.TestGroup.from_list(
    group_id=vts.ComplianceTestGroup.GROUP_DISPLAYPORT_1_4_DISPLAYID_CTS_SOURCE_TEST,
    name="DP 1.4 DisplayID CTS Source Test Set",
    test_list=[
        (0, "4.7.1.1", "Basic supported formats"),
        (1, "4.7.1.2", "Preferred timing"),
        (2, "4.7.1.3", "Out-of-range request"),
        (3, "4.7.1.4", "Invalid EDID"),
        (4, "4.7.2.1", "Audio - Basic Supported Formats"),
        (5, "4.7.2.2", "Audio - Out-of-Range Request"),
        (6, "4.7.3.1", "EDID Read with More than 256 Bytes of Data Including DisplayID Block"),
        (7, "4.7.3.2", "EDID Read with Greater than 8 Blocks of Data, Including DisplayID Block"),
        (8, "4.7.3.3", "EDID Read with Unknown Extensions and Unknown Data Blocks, Including DisplayID Block"),
        (9, "4.7.4.1", "DisplayID Detailed Timing Support"),
        (10, "4.7.5.1", "DisplayID Adaptive-Sync CVT RB v3 Support"),
    ]
)

DP_2_1_LL_SOURCE_DUT_CTS = compliance_tests_manager.TestGroup.from_list(
    group_id=vts.ComplianceTestGroup.GROUP_DISPLAYPORT_2_1_LINK_LAYER_SOURCE_DUT_CTS,
    name="DP 2.1 Link Layer Source DUT CTS",
    test_list=[
        (0, "4.2.1.1", "Source DUT Retry on No-Reply During AUX Read after HPD Plug Event (3200us)"),
        (1, "4.2.1.2", "Source Retry on Invalid Reply During AUX Read after HPD Plug Event"),
        (2, "4.2.1.3", "Source Device HPD Event Pulse Length Test"),
        (3, "4.2.1.4", "Source Device IRQ_HPD Pulse Length Test"),
        (4, "4.2.1.5", "Source Device Inactive HPD"),
        (5, "4.2.2.1", "DPCD Receiver Capability and EDID Read upon HPD Plug Event"),
        (6, "4.2.2.2", "DPCD Receiver Capability Read upon HPD Plug Event"),
        (7, "4.2.2.4", "EDID Read Failure #1: I2C-Over-AUX NACK"),
        (8, "4.2.2.5", "EDID Read Failure #2: I2C-Over-AUX DEFER"),
        (9, "4.2.2.7", "Branch Device Detection upon HPD Plug Event"),
        (10, "4.2.2.8", "EDID Read on IRQ HPD Event after Branch Device Detection"),
        (11, "4.2.2.10", "Link Status-Adjust Request AUX read interval during Link Training"),
        (12, "4.2.2.11", "Various UHBR AUX read interval verification in first EQ loop"),
        (13, "4.2.2.12", "UHBR Link Status/Adjust different FFE Request, different AUX read interval for 10 EQ loop"),
        (14, "4.3.1.1", "Successful Link Training at All Supported Lane Counts and 8b10b Link Speeds"),
        (15, "4.3.1.2", "Successful Link Training Upon HPD Plug Event"),
        (16, "4.3.1.3", "Successful Link Training with Request of Higher Differential Voltage Swing during Clock Recovery Sequence"),
        (17, "4.3.1.4", "Successful 8b10b Link Training to a Lower Link Rate/Bandwidth #1: Iterate at Maximum Voltage Swing"),
        (18, "4.3.1.5", "Successful 8b10b Link Training to a Lower Link Rate/Bandwidth #2: Iterate at Minimum Voltage Swing"),
        (19, "4.3.1.6", "Successful 8b10b Link Training with Request of a Higher Pre-emphasis Setting During Channel Equalization Sequence"),
        (20, "4.3.1.7", "Successful 8b10b Link Training at Lower Link Rate/Bandwidth Due to Loss of Symbol Lock During Channel Equalization Sequence"),
        (21, "4.3.1.8", "Unsuccessful 8b10b Link Training at Lower Link Rate #1: Iterate at Maximum Voltage Swing"),
        (22, "4.3.1.9", "Unsuccessful 8b10b Link Training at Lower Link Rate #2: Iterate at Minimum Voltage Swing"),
        (23, "4.3.1.10", "Unsuccessful 8b10b Link Training due to Failure in Channel Equalization Sequence (loop count > 5)"),
        (24, "4.3.1.11", "Successful 8b10b Link Training with Simultaneous Request for Differential Voltage Swing and Pre-emphasis during Clock Recovery Sequence"),
        (25, "4.3.1.12", "Source Device 8b10b Link Training CR Fallback Test"),
        (26, "4.3.1.13", "Source Device 8b10b Link Training EQ Fallback Test"),
        (27, "4.3.1.14", "Successful Link Training at All Supported Lane Counts and UHBR Link Speeds"),
        (28, "4.3.1.15", "Successful Link Training Upon HPD Plug Event for UHBR speed"),
        (29, "4.3.1.16", "Successful Link Training when EQ done at 20th loop during channel EQ phase"),
        (30, "4.3.1.17", "Successful Link Training to a Lower Bandwidth, when CHANNEL_EQ_DONE bits not set in 20 loops during channel EQ phase"),
        (31, "4.3.1.18", "Successful Link Training to a Lower Bandwidth. When LT Failed received in middle of 20 loop (random value 1 to 19) during channel EQ Done"),
        (32, "4.3.1.19", "Successful Link Training to a Lower Bandwidth. When LT Failed received at 20th loop during channel EQ Done"),
        (33, "4.3.1.20", "Successful Link Training to a Lower Bandwidth. When LT Failed received at after EQ done"),
        (34, "4.3.1.21", "Successful Link Training to a Lower Bandwidth. When EQ_INTERLANE_ALIGN_DONE bit not set during EQ phase"),
        (35, "4.3.1.22", "Successful Link Training to a Lower Bandwidth. When Symbols not locked during CDS phase"),
        (36, "4.3.1.23", "Successful Link Training to a Lower Bandwidth. When CDS_INTERLANE_ALIGN_DONE bit not set during CDS phase"),
        (37, "4.3.1.24", "UHBR Fallback rate table validation"),
        (38, "4.3.2.1", "Successful Link Re-training After IRQ HPD Pulse Due to Loss of Symbol Lock"),
        (39, "4.3.2.2", "Successful Link Re-training After IRQ HPD Pulse Due to Loss of Clock Recovery Lock (Equalization Lock for 128b/132b rates)"),
        (40, "4.3.2.3", "Successful Link Re-training After IRQ HPD Pulse Due to Loss of Inter-lane Alignment Lock"),
        (41, "4.3.2.4", "Handling of IRQ HPD Pulse with No Error Status Bits Set"),
        (42, "4.3.2.5", "Lane Count Reduction"),
        (43, "4.3.3.1", "8b10b Rate Video Time Stamp Generation"),
        (44, "4.3.3.2", "UHBR Video Time Stamp Generation"),
        (45, "4.4.1.1", "8b10b Rate Pixel Data Packing and Steering"),
        (46, "4.4.1.2", "8b10b Rate Main Stream Data Packing and Stuffing Least Packed TU"),
        (47, "4.4.1.3", "8b10b Rate Main Stream Data Packing and Stuffing Most Packed TU"),
        (48, "4.4.1.4", "UHBR Rate Pixel Data Packing and Steering"),
        (49, "4.4.1.5", "UHBR Rate Main Stream Data Packing and Stuffing Least Packed MTP"),
        (50, "4.4.1.6", "UHBR Rate Main Stream Data Packing and Stuffing Most Packed MTP"),
        (51, "4.4.2.1", "8b10b Rate Main Video Stream Format Change Handling"),
        (52, "4.4.2.2", "UHBR Rate Main Video Stream Format Change Handling"),
        (53, "4.4.3", "Power Management"),
        (54, "4.4.4.2", "Audio Stream Header Synchronization"),
        (55, "4.4.4.3", "Audio Time Stamp Generation"),
        (56, "4.4.4.4", "Audio InfoFrame Packet"),
        (57, "4.4.4.5", "Audio Stream Transmission"),
        (58, "4.4.4.6", "Audio Start Sequence"),
        (59, "4.5.1.1", "FEC enable verification for all supported Lane count and Link Speed"),
        (60, "4.5.1.2", "FEC ready verification for non FEC capable sink"),
    ]
)

DP_2_1_DSC_CTS_SOURCE_DUT = compliance_tests_manager.TestGroup.from_list(
    group_id=vts.ComplianceTestGroup.GROUP_DISPLAYPORT_2_1_DSC_CTS_SOURCE_DUT,
    name="DP 2.1 DSC CTS Source DUT",
    test_list=[
        (0, "4.6.1.1", "DSC enable sequence verification"),
        (1, "4.6.1.2", "DSC PPS block prediction flag verification"),
        (2, "4.6.1.3", "DSC PPS convert RGB flag verification"),
        (3, "4.6.1.4", "DSC PPS (YCbCr 4:4:4 convert RGB =0) flag verification"),
        (4, "4.6.1.5", "DSC PPS Simple 4:2:2 flag verification"),
        (5, "4.6.1.6", "DSC PPS Native 4:2:2 flag verification"),
        (6, "4.6.1.7", "DSC PPS Native 4:2:0 flag verification"),
        (7, "4.6.1.8", "DSC PPS convert RGB flag verification for DSC Algorithm revision 1.1"),
        (8, "4.6.1.9", "DSC PPS (YCbCr 4:4:4 convert RGB = 0) flag verification for DSC Algorithm revision 1.1"),
    ]
)

DP_2_1_DISPLAYID_CTS_SOURCE_TEST_SET = compliance_tests_manager.TestGroup.from_list(
    group_id=vts.ComplianceTestGroup.GROUP_DISPLAYPORT_2_1_DISPLAYID_CTS_SOURCE_TEST,
    name="DP 2.1 DisplayID CTS Source Test Set",
    test_list=[
        (0, "4.7.1.1", "Basic supported formats"),
        (1, "4.7.1.2", "Preferred timing"),
        (2, "4.7.1.3", "Out-of-range request"),
        (3, "4.7.1.4", "Invalid EDID"),
        (4, "4.7.2.1", "Audio - Basic Supported Formats"),
        (5, "4.7.2.2", "Audio - Out-of-Range Request"),
        (6, "4.7.3.1", "EDID Read with More than 256 Bytes of Data Including DisplayID Block"),
        (7, "4.7.3.2", "EDID Read with Greater than 8 Blocks of Data, Including DisplayID Block"),
        (8, "4.7.3.3", "EDID Read with Unknown Extensions and Unknown Data Blocks, Including DisplayID Block"),
        (9, "4.7.4.1", "DisplayID Detailed Timing Support"),
        (10, "4.7.5.1", "DisplayID Adaptive-Sync CVT RB v3 Support"),
    ]
)
