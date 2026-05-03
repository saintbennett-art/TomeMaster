"use client";
import { useState, useRef, useCallback } from 'react';
import { uploadRecording } from '@/lib/apiClient';
import { get } from 'idb-keyval';

/**
 * useScreenRecorder: Directorial Capture Logic
 * Facilitates high-fidelity viewport recording for marketing demonstrations.
 */
export function useScreenRecorder(folderPath: string | null) {
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    const startRecording = useCallback(async () => {
        let activePath = folderPath;
        
        // [SELF-HEALING HANDSHAKE]: If state is null, attempt emergency vault retrieval
        if (!activePath) {
            activePath = await get<string>('tome_master_active_folder');
        }

        if (!activePath) {
            alert(`DIRECTORIAL DEADLOCK: Project folder must be anchored before recording.\n\n[DIAGNOSTICS]:\n- React State: ${folderPath}\n- Vault Search: NOT FOUND\n\nPlease anchor your folder again.`);
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: { frameRate: { ideal: 30 } },
                audio: true
            });

            chunksRef.current = [];
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'video/webm;codecs=vp9'
            });

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunksRef.current.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                const blob = new Blob(chunksRef.current, { type: 'video/webm' });
                
                // [DIRECTORIAL NAMING]: Prompt for feature name to ensure organized marketing assets
                const featureName = prompt("Directorial Capture Complete.\nEnter the name of the feature you just recorded (e.g., 'Boardroom_Audit'):", "New_Feature");
                const now = new Date();
                const dateStr = now.toISOString().split('T')[0]; // YYYY-MM-DD
                const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '-').substring(0, 5); // HH-MM
                
                const sanitizedName = (featureName || "Demo").trim().replace(/[^a-z0-9]/gi, '_');
                const filename = `TomeMaster_${sanitizedName}_${dateStr}_${timeStr}.webm`;
                
                const file = new File([blob], filename, { type: 'video/webm' });
                
                // Stop all tracks to clear the "sharing" notification
                stream.getTracks().forEach(track => track.stop());
                
                // Re-verify path before upload
                let uploadPath = folderPath;
                if (!uploadPath) {
                    uploadPath = await get<string>('tome_master_active_folder');
                }

                if (uploadPath) {
                    await uploadRecording(file, uploadPath);
                }

                setIsRecording(false);
                setRecordingTime(0);
                if (timerRef.current) clearInterval(timerRef.current);
            };

            mediaRecorderRef.current = mediaRecorder;
            mediaRecorder.start();
            setIsRecording(true);
            
            setRecordingTime(0);
            timerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);

        } catch (err) {
            console.error("Directorial Capture Failure:", err);
            setIsRecording(false);
        }
    }, [folderPath]);

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
        }
    }, [isRecording]);

    return {
        isRecording,
        recordingTime,
        startRecording,
        stopRecording
    };
}
