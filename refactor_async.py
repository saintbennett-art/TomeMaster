import re

file_path = r"c:\Users\saint\.gemini\antigravity\playground\dark-schrodinger\backend\services\transcriber_service.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# The section we want to replace starts with:
#         for i, f_path in enumerate(all_files):
#             # Check if we should pause for user input in Live Mode
#             while TRANSCRIPTION_STATE.get("waiting_for_input"):
#                 time.sleep(1)

# And ends at:
#         # [SOVEREIGN FINAL STITCH]: Unify all physical artifacts (0-498) into the editor
#         print("BOARDROOM: Mission Success. Executing Final Physical Stitch...")

# We will locate these anchors.
start_marker = '        for i, f_path in enumerate(all_files):\n            # Check if we should pause for user input in Live Mode'
end_marker = '        # [SOVEREIGN FINAL STITCH]: Unify all physical artifacts (0-498) into the editor'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Could not find markers!")
    print("Start:", start_idx)
    print("End:", end_idx)
    exit(1)

new_logic = """        async def _consumer(queue):
            while True:
                job = await queue.get()
                i, f_path = job
                
                # Check if we should pause for user input in Live Mode
                while TRANSCRIPTION_STATE.get("waiting_for_input"):
                    await asyncio.sleep(1)
                
                try:
                    batch = [f_path]
                    
                    # 1. Systemic Image Processing & Telemetry Generation
                    for f_idx, f in enumerate(batch):
                        images_to_process = []
                        
                        if f.lower().endswith(".pdf"):
                            pdf_doc = fitz.open(f)
                            for page_num in range(len(pdf_doc)):
                                page = pdf_doc.load_page(page_num)
                                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                images_to_process.append((img, f"{f}_p{page_num+1}"))
                            pdf_doc.close()
                        else:
                            try:
                                with Image.open(f) as img_check:
                                    img_check.verify()
                                with Image.open(f) as img:
                                    img.load() 
                                    images_to_process.append((img.copy(), f))
                            except Exception as e:
                                print(f"BOARDROOM CRITICAL: Asset Corruption Detected: {os.path.basename(f)}. Isolating...")
                                failed_dir = os.path.join(folder_path, "Failed_Assets")
                                os.makedirs(failed_dir, exist_ok=True)
                                try:
                                    import shutil
                                    shutil.move(f, os.path.join(failed_dir, os.path.basename(f)))
                                    with TRANSCRIPTION_LOCK:
                                        TRANSCRIPTION_STATE["page_audits"].append({
                                            "page": f"ERR_{i}", "status": "failed",
                                            "source_file": os.path.basename(f), "error": str(e)
                                        })
                                except: pass
                            except: pass
                            continue

                    if not images_to_process:
                        continue
                            
                    for img, label in images_to_process:
                        img.thumbnail((1024, 1024))
                            
                        buffered_telemetry = io.BytesIO()
                        with img.copy() as thumb:
                            thumb.thumbnail((512, 512)) 
                            thumb.save(buffered_telemetry, format="JPEG", quality=60)
                             
                        with TRANSCRIPTION_LOCK:
                            TRANSCRIPTION_STATE["current_image_b64"] = base64.b64encode(buffered_telemetry.getvalue()).decode('utf-8')
                        
                        batch_start_time = time.time()
                        
                        try:
                            # Direct await instead of asyncio.run
                            raw_text, used_prov, used_mod = await _call_ai_with_failover(
                                img, provider, model_override, api_key,
                                fallback_provider=fallback_provider,
                                fallback_model=fallback_model
                            )
                            
                            metrics = {"total_tokens": 0}
                            duration = round(time.time() - batch_start_time, 2)
                            _log_api_usage("Transcriber", used_prov, used_mod, metrics, folder_path, duration)
                        except Exception as failover_e:
                            with TRANSCRIPTION_LOCK:
                                TRANSCRIPTION_STATE["status"] = "error"
                                TRANSCRIPTION_STATE["error_message"] = f"Spectrum Blackout: {str(failover_e)}"
                            return

                        with TRANSCRIPTION_LOCK:
                            TRANSCRIPTION_STATE["current_extracted_text"] = raw_text.strip()
                            TRANSCRIPTION_STATE["is_new_chunk"] = True
                            
                        pages = re.findall(r'<page>.*?</page>', raw_text, re.DOTALL)
                        for p_idx, p in enumerate(pages):
                            num_match = re.search(r'<number>(.*?)</number>', p, re.DOTALL)
                            text_match = re.search(r'<text>(.*?)</text>', p, re.DOTALL)
                            if num_match and text_match:
                                t_text = text_match.group(1).strip()
                                extracted_num = num_match.group(1).strip()
                                
                                final_page_num = extracted_num
                                if extracted_num.isdigit():
                                    final_page_num = str(int(extracted_num) + TRANSCRIPTION_STATE["offset_delta"])

                                if save_page_artifact(folder_path, final_page_num, t_text, label, i):
                                    page_data = {
                                        "extracted_page_number": final_page_num,
                                        "raw_extracted_number": extracted_num,
                                        "text": t_text,
                                        "preview": " ".join(t_text.split()[:10]) + "..." if t_text else "",
                                        "source_file": os.path.basename(label),
                                        "physical_index": i
                                    }
                                    with TRANSCRIPTION_LOCK:
                                        master_pages.append(page_data)
                                else:
                                    print(f"BOARDROOM WARNING: Physical Save Failed for page {final_page_num}.")

                    with TRANSCRIPTION_LOCK:
                        TRANSCRIPTION_STATE["processed_images"] += 1
                        TRANSCRIPTION_STATE["last_processed_file"] = os.path.basename(label)
                        TRANSCRIPTION_STATE["error_message"] = f"Page {TRANSCRIPTION_STATE['processed_images']} of {total_files} digitized — {os.path.basename(label)}"
                        TRANSCRIPTION_STATE["pages"] = list(master_pages)
                        TRANSCRIPTION_STATE["page_audits"] = [
                            {"page": p.get("extracted_page_number", "?"), "preview": p.get("preview", ""), "source_file": p.get("source_file", "unknown")} 
                            for p in master_pages
                        ]
                    
                    try:
                        import threading
                        temp_cache = cache_file + f".tmp_{threading.get_ident()}"
                        with TRANSCRIPTION_LOCK:
                            master_pages_copy = list(master_pages)
                        
                        with open(temp_cache, "w", encoding="utf-8") as f:
                            json.dump({"processed_index": i + len(batch), "pages": master_pages_copy}, f)
                            f.flush()
                            os.fsync(f.fileno())
                        
                        max_rename_retries = 5
                        for retry in range(max_rename_retries):
                            try:
                                if os.path.exists(cache_file):
                                    os.replace(temp_cache, cache_file)
                                else:
                                    os.rename(temp_cache, cache_file)
                                break
                            except PermissionError:
                                if retry == max_rename_retries - 1:
                                    print(f"BOARDROOM WARNING: Persistent Permission Denied on cache update.")
                                else:
                                    time.sleep(0.5)
                    except Exception as disk_e:
                        print(f"CRITICAL DISK ERROR: Failed to update cache. {disk_e}")
                    finally:
                        if os.path.exists(temp_cache):
                            try: os.remove(temp_cache)
                            except: pass
                    
                    try:
                        archive_dir = os.path.join(folder_path, TRANSCRIPTION_ARTIFACTS_DIR)
                        if not os.path.exists(archive_dir):
                            os.makedirs(archive_dir)
                        
                        dest_path = os.path.join(archive_dir, os.path.basename(label))
                        if os.path.exists(dest_path):
                            if os.path.exists(label):
                                os.remove(label)
                        else:
                            if os.path.exists(label):
                                shutil.move(label, dest_path)
                    except Exception as move_e:
                        print(f"BOARDROOM WARNING: Failed to archive image {label}: {move_e}")

                except Exception as loop_e:
                    with TRANSCRIPTION_LOCK:
                        TRANSCRIPTION_STATE["status"] = "error"
                        TRANSCRIPTION_STATE["error_message"] = str(loop_e)
                    print(f"BOARDROOM ERROR: Async worker exception: {loop_e}")
                finally:
                    queue.task_done()

        async def _async_orchestrator():
            queue = asyncio.Queue()
            jobs_queued = 0
            
            for i, f_path in enumerate(all_files):
                rtf_name_0 = f"page_{i}.rtf"
                rtf_name_1 = f"page_{i+1}.rtf"
                if rtf_name_0.lower() in existing_rtfs or rtf_name_1.lower() in existing_rtfs:
                    with TRANSCRIPTION_LOCK:
                        if TRANSCRIPTION_STATE["processed_images"] <= i:
                            TRANSCRIPTION_STATE["processed_images"] = i + 1
                            TRANSCRIPTION_STATE["current_batch"] = i + 1
                            if i % 10 == 0 or i == total_files - 1:
                                TRANSCRIPTION_STATE["error_message"] = f"Verified {i + 1} of {total_files} — {os.path.basename(f_path)} already sealed."
                    continue
                queue.put_nowait((i, f_path))
                jobs_queued += 1
                
            if jobs_queued == 0:
                return
                
            num_workers = min(3, jobs_queued)
            workers = [asyncio.create_task(_consumer(queue)) for _ in range(num_workers)]
            await queue.join()
            for w in workers:
                w.cancel()

        # [SOVEREIGN INGESTION]: Run the concurrent workers
        asyncio.run(_async_orchestrator())

"""

new_content = content[:start_idx] + new_logic + content[end_idx:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Refactor successful!")
