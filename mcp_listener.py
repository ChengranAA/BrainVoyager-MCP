import socket
import json

# BrainVoyager uses different Qt wrappers depending on the version.
# This safely tries to grab the Timer from whichever one is installed.
try:
    from PyQt5.QtCore import QTimer
except ImportError:
    try:
        from PySide2.QtCore import QTimer
    except ImportError:
        from PySide6.QtCore import QTimer

HOST = '127.0.0.1'
PORT = 5050

# 1. Set up a non-blocking TCP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
server_socket.setblocking(False) # CRITICAL: This stops the UI from freezing

bv.print_to_log(f"SUCCESS: Real-time listener active on {HOST}:{PORT}")

def check_for_mcp_requests():
    try:
        client_socket, address = server_socket.accept()
        client_socket.settimeout(1.0)
        request = client_socket.recv(2048).decode('utf-8')

        # Parse the JSON body
        body = request.split("\r\n\r\n")[-1]
        data = json.loads(body)

        # Determine which action Zed is requesting
        action = data.get('action')
        target_path = data.get('path')

        # --- General Commands ---

        if action == "methods":
            bv.print_to_log("MCP requested method list.")
            method_list = bv.methods()
            response_body = json.dumps({"result": list(method_list)})
            response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "describe_method":
            method_name = data.get('method_name', '')
            bv.print_to_log(f"MCP requested description of method: {method_name}")
            doc = bv.describe_method(method_name)
            response_body = json.dumps({"result": doc})
            response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "close_all":
            bv.print_to_log("MCP instructed to close all documents.")
            bv.close_all()
            response = "HTTP/1.1 200 OK\n\nAll documents closed."
            client_socket.sendall(response.encode('utf-8'))

        # --- Document Open Commands ---

        elif action == "open_document" and target_path:
            bv.print_to_log(f"MCP instructed to open: {target_path}")
            doc = bv.open_document(target_path)
            if doc is not None:
                response = "HTTP/1.1 200 OK\n\nDocument opened successfully."
            else:
                response = "HTTP/1.1 400 Bad Request\n\nBrainVoyager rejected the file format."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "open" and target_path:
            close_current = data.get('close_current_doc', False)
            remove_current = data.get('remove_current_doc', False)
            bv.print_to_log(
                f"MCP instructed to open (close_current={close_current}, "
                f"remove_current={remove_current}): {target_path}"
            )
            doc = bv.open(
                target_path,
                close_current_doc=close_current,
                remove_current_doc=remove_current
            )
            if doc is not None:
                response = "HTTP/1.1 200 OK\n\nDocument opened successfully."
            else:
                response = "HTTP/1.1 400 Bad Request\n\nBrainVoyager rejected the file format."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "get_doc_attributes":
            doc = bv.active_document
            if doc is not None:
                bv.print_to_log(
                    f"MCP instructed to get information from document: {target_path}"
                )
                info_string = f"Document: {doc.file_name}, Dimensions: {doc.dim_x}x{doc.dim_y}x{doc.dim_z}, Voxel Size: {doc.voxelsize_x}, {doc.voxelsize_y}, {doc.voxelsize_z}, Volumes: {doc.n_volumes} (TR: {doc.TR}ms), Path: {doc.path_file_name}"
                response_body = json.dumps({"result": info_string})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            else:
                response = "HTTP/1.1 400 Bad Request\n\nFailed to create VMR document."
            client_socket.sendall(response.encode('utf-8'))

        # --- Document Creation Commands ---

        elif action == "create_vmr_dicom":
            file_of_series = data.get('file_of_series', '')
            if file_of_series:
                bv.print_to_log(
                    f"MCP instructed to create VMR from DICOM: {file_of_series}"
                )
                doc = bv.create_vmr_dicom(file_of_series)
                if doc is not None:
                    response = "HTTP/1.1 200 OK\n\nVMR document created successfully."
                else:
                    response = "HTTP/1.1 400 Bad Request\n\nFailed to create VMR document."
            else:
                response = "HTTP/1.1 400 Bad Request\n\nMissing file_of_series."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "create_vmr_dicom_nifti_bids":
            file_of_series = data.get('file_of_series', '')
            subj_id = data.get('subj_id', 1)
            ses_id = data.get('ses_id', 1)
            project_folder = data.get('project_folder', '')
            if file_of_series and project_folder:
                bv.print_to_log(
                    f"MCP instructed to create VMR NIfTI BIDS: {file_of_series} "
                    f"subj={subj_id} ses={ses_id} project={project_folder}"
                )
                nifti_path = bv.create_vmr_dicom_nifti_bids(
                    file_of_series, subj_id, ses_id, project_folder
                )
                response_body = json.dumps({"result": nifti_path})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            else:
                response = (
                    "HTTP/1.1 400 Bad Request\n\n"
                    "Missing file_of_series or project_folder."
                )
            client_socket.sendall(response.encode('utf-8'))

        elif action == "create_vmr":
            scanner_file_type = data.get('scanner_file_type', 'DICOM')
            first_file = data.get('first_file', '')
            n_slices = data.get('n_slices', 0)
            big_endian = data.get('big_endian', False)
            slice_rows = data.get('slice_rows', 0)
            slice_cols = data.get('slice_cols', 0)
            bytes_per_pixel = data.get('bytes_per_pixel', 2)
            if first_file:
                bv.print_to_log(
                    f"MCP instructed to create VMR: type={scanner_file_type} "
                    f"file={first_file}"
                )
                doc = bv.create_vmr(
                    scanner_file_type, first_file, n_slices,
                    big_endian, slice_rows, slice_cols, bytes_per_pixel
                )
                if doc is not None:
                    response = "HTTP/1.1 200 OK\n\nVMR document created successfully."
                else:
                    response = "HTTP/1.1 400 Bad Request\n\nFailed to create VMR document."
            else:
                response = "HTTP/1.1 400 Bad Request\n\nMissing first_file."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "create_amr":
            scanner_file_type = data.get('scanner_file_type', 'DICOM')
            first_file = data.get('first_file', '')
            n_slices = data.get('n_slices', 0)
            big_endian = data.get('big_endian', False)
            slice_rows = data.get('slice_rows', 0)
            slice_cols = data.get('slice_cols', 0)
            bytes_per_pixel = data.get('bytes_per_pixel', 2)
            if first_file:
                bv.print_to_log(
                    f"MCP instructed to create AMR: type={scanner_file_type} "
                    f"file={first_file}"
                )
                doc = bv.create_amr(
                    scanner_file_type, first_file, n_slices,
                    big_endian, slice_rows, slice_cols, bytes_per_pixel
                )
                if doc is not None:
                    response = "HTTP/1.1 200 OK\n\nAMR document created successfully."
                else:
                    response = "HTTP/1.1 400 Bad Request\n\nFailed to create AMR document."
            else:
                response = "HTTP/1.1 400 Bad Request\n\nMissing first_file."
            client_socket.sendall(response.encode('utf-8'))

        # --- VMR Document Methods ---

        elif action == "vmr_deface":
            vmr = bv.active_document
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log("MCP instructed to deface active VMR.")
                result = vmr.deface()
                response_body = json.dumps({"result": result})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_transform_to_std_sag":
            vmr = bv.active_document
            out_filename = data.get('out_vmr_sag_filename', '')
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            elif not out_filename:
                response = "HTTP/1.1 400 Bad Request\n\nMissing out_vmr_sag_filename."
            else:
                bv.print_to_log(
                    f"MCP instructed to transform VMR to std sag: {out_filename}"
                )
                result = vmr.transform_to_std_sag(out_filename)
                response_body = json.dumps({"result": result})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_transform_to_std_isovoxel":
            vmr = bv.active_document
            interpolation = data.get('interpolation_method', 1)
            out_filename = data.get('out_vmr_iso_filename', '')
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            elif not out_filename:
                response = "HTTP/1.1 400 Bad Request\n\nMissing out_vmr_iso_filename."
            else:
                bv.print_to_log(
                    f"MCP instructed to transform VMR to std isovoxel (1mm): "
                    f"{out_filename}"
                )
                result = vmr.transform_to_std_isovoxel(interpolation, out_filename)
                response_body = json.dumps({"result": result})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_transform_to_isovoxel":
            vmr = bv.active_document
            target_res = data.get('target_res', 1.0)
            framing_cube_dim = data.get('framing_cube_dim', 256)
            interpolation = data.get('interpolation_method', 1)
            out_filename = data.get('out_vmr_iso_filename', '')
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            elif not out_filename:
                response = "HTTP/1.1 400 Bad Request\n\nMissing out_vmr_iso_filename."
            else:
                bv.print_to_log(
                    f"MCP instructed to transform VMR to isovoxel "
                    f"(res={target_res}, cube={framing_cube_dim}): {out_filename}"
                )
                result = vmr.transform_to_isovoxel(
                    target_res, framing_cube_dim, interpolation, out_filename
                )
                response_body = json.dumps({"result": result})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_correct_intensity_inhomogeneities":
            vmr = bv.active_document
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log(
                    "MCP instructed to correct intensity inhomogeneities."
                )
                result = vmr.correct_intensity_inhomogeneities()
                response_body = json.dumps({"result": result})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_correct_intensity_inhomogeneities_ext":
            vmr = bv.active_document
            include_brain_extraction = data.get('include_brain_extraction', True)
            n_cycles = data.get('n_cycles', 3)
            tissue_range_thresh = data.get('tissue_range_thresh', 0.25)
            intensity_thresh = data.get('intensity_thresh', 0.3)
            fit_polynom_order = data.get('fit_polynom_order', 3)
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log(
                    f"MCP instructed to correct intensity inhomogeneities "
                    f"(ext): cycles={n_cycles}, brain_extr={include_brain_extraction}"
                )
                result = vmr.correct_intensity_inhomogeneities_ext(
                    include_brain_extraction, n_cycles,
                    tissue_range_thresh, intensity_thresh, fit_polynom_order
                )
                response_body = json.dumps({"result": result})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_normalize_to_mni_space":
            vmr = bv.active_document
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log("MCP instructed to normalize VMR to MNI space.")
                result = vmr.normalize_to_mni_space()
                response_body = json.dumps({"result": result})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_auto_acpc_tal_transformation":
            vmr = bv.active_document
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log(
                    "MCP instructed to perform auto ACPC/Talairach transformation."
                )
                result = vmr.auto_acpc_tal_transformation()
                response_body = json.dumps({"result": result})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_get_volume_data_as_byte_buffer":
            vmr = bv.active_document
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log("MCP requested VMR volume data as byte buffer.")
                data_list = vmr.get_volume_data_as_byte_buffer()
                response_body = json.dumps({"result": list(data_list)})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_get_volume_data_as_int_list":
            vmr = bv.active_document
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log("MCP requested VMR volume data as int list.")
                data_list = vmr.get_volume_data_as_int_list()
                response_body = json.dumps({"result": list(data_list)})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_get_volume_data_as_float_list":
            vmr = bv.active_document
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log("MCP requested VMR volume data as float list.")
                data_list = vmr.get_volume_data_as_float_list()
                response_body = json.dumps({"result": list(data_list)})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_get_volume_data_as_float64_list":
            vmr = bv.active_document
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log("MCP requested VMR volume data as float64 list.")
                data_list = vmr.get_volume_data_as_float64_list()
                response_body = json.dumps({"result": list(data_list)})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_get_voxel_intensity":
            vmr = bv.active_document
            x = data.get('x', 0)
            y = data.get('y', 0)
            z = data.get('z', 0)
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log(
                    f"MCP requested voxel intensity at ({x}, {y}, {z})."
                )
                value = vmr.get_voxel_intensity(x, y, z)
                response_body = json.dumps({"result": value})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_set_voxel_intensity":
            vmr = bv.active_document
            x = data.get('x', 0)
            y = data.get('y', 0)
            z = data.get('z', 0)
            value = data.get('value', 0)
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log(
                    f"MCP instructed to set voxel intensity "
                    f"at ({x}, {y}, {z}) to {value}."
                )
                vmr.set_voxel_intensity(x, y, z, value)
                response = "HTTP/1.1 200 OK\n\nVoxel intensity set."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_create_mesh_scene":
            vmr = bv.active_document
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                bv.print_to_log("MCP instructed to create mesh scene for VMR.")
                mesh_scene = vmr.create_mesh_scene()
                if mesh_scene is not None:
                    response = (
                        "HTTP/1.1 200 OK\n\n"
                        "Mesh scene created/retrieved successfully."
                    )
                else:
                    response = (
                        "HTTP/1.1 400 Bad Request\n\n"
                        "Failed to create mesh scene."
                    )
            client_socket.sendall(response.encode('utf-8'))

        elif action == "vmr_update_viewer":
            vmr = bv.active_document
            if vmr is None:
                response = "HTTP/1.1 400 Bad Request\n\nNo active VMR document."
            else:
                vmr.update_viewer()
                response = "HTTP/1.1 200 OK\n\nVMR viewer updated."
            client_socket.sendall(response.encode('utf-8'))

        # --- DICOM Commands ---

        elif action == "rename_dicoms" and target_path:
            bv.print_to_log(f"MCP instructed to rename DICOMs in: {target_path}")
            bv.rename_dicoms(target_path)
            response = "HTTP/1.1 200 OK\n\nDICOM renaming process initiated."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "anonymize_dicoms":
            target_path = data.get('path')
            patient_name = data.get('patient_name', '')
            if target_path and patient_name:
                bv.print_to_log(
                    f"MCP instructed to anonymize DICOMs in: {target_path} "
                    f"as '{patient_name}'"
                )
                bv.anonymize_dicoms(target_path, patient_name)
                response = "HTTP/1.1 200 OK\n\nDICOM anonymization process initiated."
            else:
                response = "HTTP/1.1 400 Bad Request\n\nMissing path or patient_name."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "deface_anat_dicoms":
            input_dir = data.get('input_directory')
            output_dir = data.get('output_directory')
            if input_dir and output_dir:
                bv.print_to_log(
                    f"MCP instructed to deface DICOMs: {input_dir} -> {output_dir}"
                )
                result = bv.deface_anat_dicoms(input_dir, output_dir)
                response_body = json.dumps({"result": result})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            else:
                response = "HTTP/1.1 400 Bad Request\n\nMissing input_directory or output_directory."
            client_socket.sendall(response.encode('utf-8'))

        # --- Log Pane Commands ---

        elif action == "show_log_pane":
            bv.show_log_pane()
            response = "HTTP/1.1 200 OK\n\nLog pane shown."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "hide_log_pane":
            bv.hide_log_pane()
            response = "HTTP/1.1 200 OK\n\nLog pane hidden."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "print_to_log":
            text = data.get('text', '')
            bv.print_to_log(text)
            response = "HTTP/1.1 200 OK\n\nText printed to log."
            client_socket.sendall(response.encode('utf-8'))

        # --- Shell Command ---

        elif action == "run_cmd":
            shell_cmd = data.get('shell_command', '')
            bv.print_to_log(f"MCP instructed to run shell command: {shell_cmd}")
            output = bv.run_cmd(shell_cmd)
            response_body = json.dumps({"result": output})
            response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        # --- Application Control ---

        elif action == "exit":
            bv.print_to_log("MCP instructed BrainVoyager to exit.")
            response = "HTTP/1.1 200 OK\n\nExiting BrainVoyager."
            client_socket.sendall(response.encode('utf-8'))
            client_socket.close()
            bv.exit()

        # --- Dialog / Message Commands ---

        elif action == "show_message_box":
            message = data.get('message', '')
            bv.show_message_box(message)
            response = "HTTP/1.1 200 OK\n\nMessage box shown."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "show_timeout_message_box":
            message = data.get('message', '')
            duration = data.get('duration', 3000)
            result = bv.show_timeout_message_box(message, duration)
            response_body = json.dumps({"result": result})
            response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        # --- Window Control ---

        elif action == "move_window":
            new_x = data.get('new_x', 0)
            new_y = data.get('new_y', 0)
            bv.move_window(new_x, new_y)
            response = "HTTP/1.1 200 OK\n\nWindow moved."
            client_socket.sendall(response.encode('utf-8'))

        elif action == "resize_window":
            new_width = data.get('new_width', 800)
            new_height = data.get('new_height', 600)
            bv.resize_window(new_width, new_height)
            response = "HTTP/1.1 200 OK\n\nWindow resized."
            client_socket.sendall(response.encode('utf-8'))

        # --- File / Directory Choosers ---

        elif action == "choose_directory":
            instruction = data.get('instruction', 'Select a directory')
            chosen = bv.choose_directory(instruction)
            response_body = json.dumps({"result": chosen})
            response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        elif action == "choose_file":
            instruction = data.get('instruction', 'Select a file')
            filter_str = data.get('filter', '*')
            chosen = bv.choose_file(instruction, filter_str)
            response_body = json.dumps({"result": chosen})
            response = f"HTTP/1.1 200 OK\n\n{response_body}"
            client_socket.sendall(response.encode('utf-8'))

        # --- MDM / VTCs ---

        elif action == "get_vtcs_of_mdm":
            mdm_file = data.get('mdm_file', '')
            if mdm_file:
                vtcs = bv.get_vtcs_of_mdm(mdm_file)
                response_body = json.dumps({"result": list(vtcs)})
                response = f"HTTP/1.1 200 OK\n\n{response_body}"
            else:
                response = "HTTP/1.1 400 Bad Request\n\nMissing mdm_file."
            client_socket.sendall(response.encode('utf-8'))

        # --- Catch-all ---

        else:
            response = "HTTP/1.1 400 Bad Request\n\nInvalid action or missing path."
            client_socket.sendall(response.encode('utf-8'))

    except BlockingIOError:
        pass
    except Exception as e:
        if not isinstance(e, json.JSONDecodeError):
            bv.print_to_log(f"Listener caught an error: {e}")
    finally:
        try:
            client_socket.close()
        except:
            pass

# 3. Hijack the BrainVoyager UI event loop
# This tells BrainVoyager: "Every 100 milliseconds, run my check function"
mcp_timer = QTimer()
mcp_timer.timeout.connect(check_for_mcp_requests)
mcp_timer.start(100)