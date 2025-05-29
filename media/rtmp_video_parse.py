import os
import struct
import sys

# (BitReader class goes here, copy it from previous response)
class BitReader:
    def __init__(self, data):
        self.data = data
        self.byte_pos = 0
        self.bit_pos = 0

    def read_bit(self):
        if self.byte_pos >= len(self.data):
            raise IndexError("End of data reached while reading bit.")

        byte = self.data[self.byte_pos]
        bit = (byte >> (7 - self.bit_pos)) & 0x01

        self.bit_pos += 1
        if self.bit_pos == 8:
            self.bit_pos = 0
            self.byte_pos += 1
        return bit

    def read_bits(self, num_bits):
        result = 0
        for _ in range(num_bits):
            result = (result << 1) | self.read_bit()
        return result

    def read_ue(self): # Unsigned Exp-Golomb
        leading_zeros = 0
        while self.read_bit() == 0 and self.byte_pos < len(self.data):
            leading_zeros += 1
        
        if leading_zeros == 0:
            return 0
        
        suffix = self.read_bits(leading_zeros)
        return (1 << leading_zeros) - 1 + suffix

    def read_se(self): # Signed Exp-Golomb
        val = self.read_ue()
        if val % 2 == 0:
            return -(val // 2)
        else:
            return (val + 1) // 2

    def align_byte(self):
        if self.bit_pos != 0:
            self.bit_pos = 0
            self.byte_pos += 1

# (parse_h264_sps and parse_h264_pps functions go here, copy them from previous response)
def parse_h264_sps(sps_nalu_data):
    """
    解析 H.264 SPS NALU 的数据部分，提取关键参数。
    Args:
        sps_nalu_data (bytes): SPS NALU 的原始数据，**包含 NALU header 字节 (0x67)**。
    Returns:
        dict: 包含解析出的 SPS 参数。
    """
    # Verify NALU type (0x67 for SPS)
    if not sps_nalu_data or (sps_nalu_data[0] & 0x1F) != 7:
        print("Error: Not a valid SPS NALU data provided.")
        return None

    reader = BitReader(sps_nalu_data[1:]) # Skip the NALU header byte (nal_unit_type + nal_ref_idc)
    sps_info = {}

    try:
        sps_info['profile_idc'] = reader.read_bits(8)
        sps_info['constraint_set0_flag'] = reader.read_bit()
        sps_info['constraint_set1_flag'] = reader.read_bit()
        sps_info['constraint_set2_flag'] = reader.read_bit()
        sps_info['constraint_set3_flag'] = reader.read_bit()
        sps_info['constraint_set4_flag'] = reader.read_bit()
        sps_info['constraint_set5_flag'] = reader.read_bit()
        sps_info['reserved_zero_2bits'] = reader.read_bits(2)
        sps_info['level_idc'] = reader.read_bits(8)
        sps_info['seq_parameter_set_id'] = reader.read_ue()

        if sps_info['profile_idc'] in [100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135]:
            sps_info['chroma_format_idc'] = reader.read_ue()
            if sps_info['chroma_format_idc'] == 3:
                sps_info['separate_colour_plane_flag'] = reader.read_bit()
            sps_info['bit_depth_luma_minus8'] = reader.read_ue()
            sps_info['bit_depth_chroma_minus8'] = reader.read_ue()
            sps_info['qpprime_y_zero_transform_bypass_flag'] = reader.read_bit()
            sps_info['seq_scaling_matrix_present_flag'] = reader.read_bit()
            if sps_info['seq_scaling_matrix_present_flag']:
                # Skipping scaling list parsing for brevity
                pass
        
        sps_info['log2_max_frame_num_minus4'] = reader.read_ue()
        sps_info['pic_order_cnt_type'] = reader.read_ue()

        if sps_info['pic_order_cnt_type'] == 0:
            sps_info['log2_max_pic_order_cnt_lsb_minus4'] = reader.read_ue()
        elif sps_info['pic_order_cnt_type'] == 1:
            sps_info['delta_pic_order_always_zero_flag'] = reader.read_bit()
            sps_info['offset_for_non_ref_pic'] = reader.read_se()
            sps_info['offset_for_top_to_bottom_field'] = reader.read_se()
            sps_info['num_ref_frames_in_pic_order_cnt_cycle'] = reader.read_ue()
            for i in range(sps_info['num_ref_frames_in_pic_order_cnt_cycle']):
                reader.read_se() # offset_for_ref_frame[i]
        
        sps_info['num_ref_frames'] = reader.read_ue()
        sps_info['gaps_in_frame_num_value_allowed_flag'] = reader.read_bit()

        sps_info['pic_width_in_mbs_minus1'] = reader.read_ue()
        sps_info['pic_height_in_map_units_minus1'] = reader.read_ue()
        sps_info['frame_mbs_only_flag'] = reader.read_bit()

        if not sps_info['frame_mbs_only_flag']:
            sps_info['mb_adaptive_frame_field_flag'] = reader.read_bit()
        sps_info['direct_8x8_inference_flag'] = reader.read_bit()
        sps_info['frame_cropping_flag'] = reader.read_bit()
        
        if sps_info['frame_cropping_flag']:
            sps_info['frame_crop_left_offset'] = reader.read_ue()
            sps_info['frame_crop_right_offset'] = reader.read_ue()
            sps_info['frame_crop_top_offset'] = reader.read_ue()
            sps_info['frame_crop_bottom_offset'] = reader.read_ue()
        
        sps_info['vui_parameters_present_flag'] = reader.read_bit()

        if sps_info['vui_parameters_present_flag']:
            vui_info = {}
            vui_info['aspect_ratio_info_present_flag'] = reader.read_bit()
            if vui_info['aspect_ratio_info_present_flag']:
                vui_info['aspect_ratio_idc'] = reader.read_bits(8)
                if vui_info['aspect_ratio_idc'] == 255:
                    vui_info['sar_width'] = reader.read_bits(16)
                    vui_info['sar_height'] = reader.read_bits(16)
            
            vui_info['overscan_info_present_flag'] = reader.read_bit()
            if vui_info['overscan_info_present_flag']:
                vui_info['overscan_appropriate_flag'] = reader.read_bit()
            
            vui_info['video_signal_type_present_flag'] = reader.read_bit()
            if vui_info['video_signal_type_present_flag']:
                vui_info['video_format'] = reader.read_bits(3)
                vui_info['video_full_range_flag'] = reader.read_bit()
                vui_info['colour_description_present_flag'] = reader.read_bit()
                if vui_info['colour_description_present_flag']:
                    vui_info['colour_primaries'] = reader.read_bits(8)
                    vui_info['transfer_characteristics'] = reader.read_bits(8)
                    vui_info['matrix_coefficients'] = reader.read_bits(8)
            
            vui_info['chroma_loc_info_present_flag'] = reader.read_bit()
            if vui_info['chroma_loc_info_present_flag']:
                vui_info['chroma_sample_loc_type_top_field'] = reader.read_ue()
                vui_info['chroma_sample_loc_type_bottom_field'] = reader.read_ue()
            
            vui_info['timing_info_present_flag'] = reader.read_bit()
            if vui_info['timing_info_present_flag']:
                vui_info['num_units_in_tick'] = reader.read_bits(32)
                vui_info['time_scale'] = reader.read_bits(32)
                vui_info['fixed_frame_rate_flag'] = reader.read_bit()
            
            sps_info['vui_parameters'] = vui_info

        # Calculate resolution
        sps_info['width'] = (sps_info['pic_width_in_mbs_minus1'] + 1) * 16
        sps_info['height'] = (2 - sps_info['frame_mbs_only_flag']) * \
                             (sps_info['pic_height_in_map_units_minus1'] + 1) * 16

        if sps_info['frame_cropping_flag']:
            crop_unit_x = 1
            crop_unit_y = 2
            if sps_info.get('chroma_format_idc') == 0:
                crop_unit_x = 1
                crop_unit_y = 1
            elif sps_info.get('chroma_format_idc') == 1:
                crop_unit_x = 2
                if sps_info['frame_mbs_only_flag'] == 0 and sps_info.get('mb_adaptive_frame_field_flag') == 0:
                     crop_unit_y = 2
                else:
                    crop_unit_y = 2 * (2 - sps_info['frame_mbs_only_flag'])
            elif sps_info.get('chroma_format_idc') == 2:
                crop_unit_x = 2
                crop_unit_y = 2 * (2 - sps_info['frame_mbs_only_flag'])
            elif sps_info.get('chroma_format_idc') == 3:
                crop_unit_x = 1
                crop_unit_y = 1

            sps_info['cropped_width'] = sps_info['width'] - \
                                        (sps_info['frame_crop_left_offset'] + sps_info['frame_crop_right_offset']) * crop_unit_x
            sps_info['cropped_height'] = sps_info['height'] - \
                                         (sps_info['frame_crop_top_offset'] + sps_info['frame_crop_bottom_offset']) * crop_unit_y
        else:
            sps_info['cropped_width'] = sps_info['width']
            sps_info['cropped_height'] = sps_info['height']

        if 'vui_parameters' in sps_info and sps_info['vui_parameters'].get('timing_info_present_flag'):
            num_units_in_tick = sps_info['vui_parameters']['num_units_in_tick']
            time_scale = sps_info['vui_parameters']['time_scale']
            if num_units_in_tick > 0 and time_scale > 0:
                sps_info['frame_rate'] = time_scale / (2.0 * num_units_in_tick)
            else:
                sps_info['frame_rate'] = None
        else:
            sps_info['frame_rate'] = None

    except IndexError as e:
        print(f"Error reading SPS bitstream: {e}. Data might be truncated.")
        return None
    except Exception as e:
        print(f"An error occurred during SPS parsing: {e}")
        return None

    return sps_info

def parse_h264_pps(pps_nalu_data):
    """
    解析 H.264 PPS NALU 的数据部分，提取关键参数。
    Args:
        pps_nalu_data (bytes): PPS NALU 的原始数据，**包含 NALU header 字节 (0x68)**。
    Returns:
        dict: 包含解析出的 PPS 参数。
    """
    # Verify NALU type (0x68 for PPS)
    if not pps_nalu_data or (pps_nalu_data[0] & 0x1F) != 8:
        print("Error: Not a valid PPS NALU data provided.")
        return None

    reader = BitReader(pps_nalu_data[1:]) # Skip NALU header byte (nal_unit_type + nal_ref_idc)
    pps_info = {}

    try:
        pps_info['pic_parameter_set_id'] = reader.read_ue()
        pps_info['seq_parameter_set_id'] = reader.read_ue()

        pps_info['entropy_coding_mode_flag'] = reader.read_bit()
        pps_info['bottom_field_pic_order_in_frame_present_flag'] = reader.read_bit()
        pps_info['num_slice_groups_minus1'] = reader.read_ue()

        if pps_info['num_slice_groups_minus1'] > 0:
            pass # Slice group map type and related fields (complex, skipping)

        pps_info['num_ref_idx_l0_active_minus1'] = reader.read_ue()
        pps_info['num_ref_idx_l1_active_minus1'] = reader.read_ue()
        pps_info['weighted_pred_flag'] = reader.read_bit()
        pps_info['weighted_bipred_idc'] = reader.read_bits(2)
        pps_info['pic_init_qp_minus26'] = reader.read_se()
        pps_info['pic_init_qs_minus26'] = reader.read_se()
        pps_info['chroma_qp_index_offset'] = reader.read_se()
        pps_info['deblocking_filter_control_present_flag'] = reader.read_bit()
        pps_info['constrained_intra_pred_flag'] = reader.read_bit()
        pps_info['redundant_pic_cnt_present_flag'] = reader.read_bit()

    except IndexError as e:
        print(f"Error reading PPS bitstream: {e}. Data might be truncated.")
        return None
    except Exception as e:
        print(f"An error occurred during PPS parsing: {e}")
        return None

    return pps_info

def parse_avc_decoder_configuration_record(record_bytes):
    """
    解析 AVCDecoderConfigurationRecord 字节流，提取 SPS 和 PPS NALU 数据。

    Args:
        record_bytes (bytes): AVCDecoderConfigurationRecord 的原始字节流。

    Returns:
        dict: 包含 SPS 和 PPS NALU 数据的字典。
              {
                  'profile_idc': int,
                  'level_idc': int,
                  'length_size_minus_one': int,
                  'sps_nalus': [bytes, ...],
                  'pps_nalus': [bytes, ...]
              }
    """
    if not record_bytes or len(record_bytes) < 7:
        print("Error: Invalid AVCDecoderConfigurationRecord data (too short).")
        return None

    record_info = {}
    offset = 0

    record_info['configurationVersion'] = record_bytes[offset]
    offset += 1
    record_info['AVCProfileIndication'] = record_bytes[offset]
    offset += 1
    record_info['profile_compatibility'] = record_bytes[offset]
    offset += 1
    record_info['AVCLevelIndication'] = record_bytes[offset]
    offset += 1
    record_info['lengthSizeMinusOne'] = record_bytes[offset] & 0x03 # Lower 2 bits
    offset += 1

    # Number of SPS NALUs
    numOfSequenceParameterSets = record_bytes[offset] & 0x1F # Lower 5 bits
    offset += 1
    record_info['sps_nalus'] = []

    for _ in range(numOfSequenceParameterSets):
        if offset + 2 > len(record_bytes):
            print("Error: Incomplete SPS length field in AVCDecoderConfigurationRecord.")
            return None
        sps_length = struct.unpack('>H', record_bytes[offset : offset + 2])[0]
        offset += 2
        if offset + sps_length > len(record_bytes):
            print("Error: Incomplete SPS data in AVCDecoderConfigurationRecord.")
            return None
        sps_nalu_data = record_bytes[offset : offset + sps_length]
        record_info['sps_nalus'].append(sps_nalu_data)
        offset += sps_length

    # Number of PPS NALUs
    numOfPictureParameterSets = record_bytes[offset] & 0xFF
    offset += 1
    record_info['pps_nalus'] = []

    for _ in range(numOfPictureParameterSets):
        if offset + 2 > len(record_bytes):
            print("Error: Incomplete PPS length field in AVCDecoderConfigurationRecord.")
            return None
        pps_length = struct.unpack('>H', record_bytes[offset : offset + 2])[0]
        offset += 2
        if offset + pps_length > len(record_bytes):
            print("Error: Incomplete PPS data in AVCDecoderConfigurationRecord.")
            return None
        pps_nalu_data = record_bytes[offset : offset + pps_length]
        record_info['pps_nalus'].append(pps_nalu_data)
        offset += pps_length

    return record_info

def parse_nalu_data(nalu_bytes):
    """
    从 H.264 NALU 字节流中解析出 NALU 单元。
    并尝试解析 SPS/PPS NALU 的内容。
    """
    parsed_nalus = []
    offset = 0

    while offset < len(nalu_bytes):
        if offset + 4 > len(nalu_bytes):
            print(f"Warning: Incomplete NALU length field at offset {offset}. Remaining bytes: {len(nalu_bytes) - offset}")
            break

        nalu_length = struct.unpack('>I', nalu_bytes[offset : offset + 4])[0]
        offset += 4

        if offset + nalu_length > len(nalu_bytes):
            print(f"Warning: Incomplete NALU data at offset {offset}. Expected {nalu_length} bytes, but only {len(nalu_bytes) - offset} available. Skipping.")
            break

        current_nalu_data = nalu_bytes[offset : offset + nalu_length]
        offset += nalu_length

        if not current_nalu_data:
            print(f"Warning: Empty NALU at offset {offset - nalu_length - 4}. Skipping.")
            continue

        nalu_header = current_nalu_data[0]
        forbidden_zero_bit = (nalu_header >> 7) & 0x01
        nal_ref_idc = (nalu_header >> 5) & 0x03
        nal_unit_type = nalu_header & 0x1F

        nalu_type_str = f"Unknown ({nal_unit_type})"
        if nal_unit_type == 1: nalu_type_str = "Coded slice of a non-IDR picture (P/B Frame)"
        elif nal_unit_type == 5: nalu_type_str = "Coded slice of an IDR picture (I Frame)"
        elif nal_unit_type == 6: nalu_type_str = "Supplemental enhancement information (SEI)"
        elif nal_unit_type == 7: nalu_type_str = "Sequence parameter set (SPS)"
        elif nal_unit_type == 8: nalu_type_str = "Picture parameter set (PPS)"
        elif nal_unit_type == 9: nalu_type_str = "Access unit delimiter"
        elif nal_unit_type == 10: nalu_type_str = "End of sequence"
        elif nal_unit_type == 11: nalu_type_str = "End of stream"

        nalu_info = {
            "nalu_type": nal_unit_type,
            "nalu_type_str": nalu_type_str,
            "nal_ref_idc": nal_ref_idc,
            "forbidden_zero_bit": forbidden_zero_bit,
            "nalu_data": current_nalu_data
        }

        # --- 新增的 SPS/PPS 解析 ---
        if nal_unit_type == 7: # SPS
            parsed_sps = parse_h264_sps(current_nalu_data)
            if parsed_sps:
                nalu_info['parsed_sps_info'] = parsed_sps
        elif nal_unit_type == 8: # PPS
            parsed_pps = parse_h264_pps(current_nalu_data)
            if parsed_pps:
                nalu_info['parsed_pps_info'] = parsed_pps
        # --- 结束新增 ---

        parsed_nalus.append(nalu_info)
    return parsed_nalus

def parse_rtmp_video_data(video_data_bytes):
    """
    解析 RTMP VideoData 字节流，并尝试解析 H.264 NALU 数据。
    Args:
        video_data_bytes (bytes): RTMP VideoData 的字节流。
    Returns:
        dict: 包含解析结果的字典。
    """
    if not video_data_bytes:
        print("Error: Empty video_data_bytes.")
        return None

    try:
        first_byte = video_data_bytes[0]
        frame_type = (first_byte >> 4) & 0x0F
        codec_id = first_byte & 0x0F

        result = {
            "frame_type": frame_type,
            "codec_id": codec_id,
            "frame_type_str": "",
            "codec_id_str": "",
            "avc_packet_type": None,
            "composition_time": None,
            "parsed_nalus": [],
            "avc_decoder_config_record": None # New field for configuration record
        }

        # Mapping FrameType
        if frame_type == 1: result["frame_type_str"] = "Keyframe"
        elif frame_type == 2: result["frame_type_str"] = "Interframe (Non-Keyframe)"
        elif frame_type == 3: result["frame_type_str"] = "Disposable Interframe"
        elif frame_type == 4: result["frame_type_str"] = "Generated Keyframe"
        else: result["frame_type_str"] = f"Unknown ({frame_type})"

        # Mapping CodecID
        if codec_id == 7: result["codec_id_str"] = "AVC (H.264)"
        elif codec_id == 12: result["codec_id_str"] = "HEVC (H.265)"
        else: result["codec_id_str"] = f"Unknown ({codec_id})"

        # Process H.264 (AVC) video data
        if codec_id == 7:
            if len(video_data_bytes) < 5:
                print("Error: Incomplete H.264 video data header.")
                return None

            avc_packet_type = video_data_bytes[1]
            composition_time = struct.unpack('>I', b'\x00' + video_data_bytes[2:5])[0]
            if composition_time & 0x800000:
                composition_time -= 0x1000000

            result["avc_packet_type"] = avc_packet_type
            result["composition_time"] = composition_time

            if avc_packet_type == 0:  # AVC sequence header (AVCDecoderConfigurationRecord)
                avc_config_record_data = video_data_bytes[5:]
                print(f"  - AVC Sequence Header (AVCDecoderConfigurationRecord) - Length: {len(avc_config_record_data)} bytes")
                
                # Parse the AVCDecoderConfigurationRecord
                parsed_config = parse_avc_decoder_configuration_record(avc_config_record_data)
                result["avc_decoder_config_record"] = parsed_config

                if parsed_config:
                    print("  --- Parsed AVCDecoderConfigurationRecord ---")
                    print(f"    Profile: {parsed_config.get('AVCProfileIndication')} (Level: {parsed_config.get('AVCLevelIndication')})")
                    for i, sps_data in enumerate(parsed_config['sps_nalus']):
                        print(f"    SPS NALU {i+1} (Length: {len(sps_data)} bytes): {sps_data.hex()}")
                        # Now, parse the *extracted* SPS NALU data using parse_h264_sps
                        parsed_sps_info = parse_h264_sps(sps_data)
                        if parsed_sps_info:
                            print("      --- Parsed SPS Info ---")
                            for k, v in parsed_sps_info.items():
                                print(f"        {k}: {v}")
                    for i, pps_data in enumerate(parsed_config['pps_nalus']):
                        print(f"    PPS NALU {i+1} (Length: {len(pps_data)} bytes): {pps_data.hex()}")
                        # Now, parse the *extracted* PPS NALU data using parse_h264_pps
                        parsed_pps_info = parse_h264_pps(pps_data)
                        if parsed_pps_info:
                            print("      --- Parsed PPS Info ---")
                            for k, v in parsed_pps_info.items():
                                print(f"        {k}: {v}")
            elif avc_packet_type == 1:  # AVC NALU
                nalu_data_raw = video_data_bytes[5:]
                print(f"  - AVC NALU Raw Data - Length: {len(nalu_data_raw)} bytes")
                result["parsed_nalus"] = parse_nalu_data(nalu_data_raw)
            elif avc_packet_type == 2:  # AVC end of sequence
                print("  - AVC End of Sequence")
            else:
                print(f"  - Unknown AVC Packet Type: {avc_packet_type}")
        else:
            print(f"  - Codec '{result['codec_id_str']}' parsing not implemented in this example.")

        return result

    except Exception as e:
        print(f"Error parsing video data: {e}")
        return None

if len(sys.argv) != 2:
    print("Usage: python rtmp_parser.py [filename]")
    sys.exit(1)
if os.path.isfile(sys.argv[1]) is False:
    print("File does not exist.")
with open(sys.argv[1], "rb") as fd:
    data = fd.read()
print("--- Parsing RTMP VideoData ---")
parsed_data = parse_rtmp_video_data(data)
print(parsed_data)
