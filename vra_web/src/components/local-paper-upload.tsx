import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Upload, AlertCircle, CheckCircle } from "lucide-react";
import { uploadApi } from "@/lib/api";
import { UploadPaperResponse } from "@/types";

interface LocalPaperUploadProps {
    onUploadSuccess: (paper: UploadPaperResponse) => void;
}

export function LocalPaperUpload({ onUploadSuccess }: LocalPaperUploadProps) {
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Reset
        setError(null);

        // Frontend Validation
        if (file.type !== "application/pdf") {
            setError("Only PDF files are supported.");
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            setError("File size cannot exceed 10MB.");
            return;
        }

        setUploading(true);

        try {
            const result = await uploadApi.uploadPaper(file);
            if (result.success) {
                onUploadSuccess(result);
                // Clear input
                if (fileInputRef.current) {
                    fileInputRef.current.value = "";
                }
            } else {
                setError(result.error || "Upload failed.");
            }
        } catch (err: any) {
            console.error("Upload error:", err);
            setError("Network error or server failure.");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="space-y-2">
            <div className="flex items-center gap-2">
                <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="gap-2"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                >
                    {uploading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <Upload className="h-4 w-4" />
                    )}
                    {uploading ? "Uploading..." : "Upload PDF"}
                </Button>
                <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept=".pdf"
                    onChange={handleFileChange}
                />
                <span className="text-xs text-muted-foreground">
                    Max 10MB. Text extracted locally.
                </span>
            </div>

            {error && (
                <div className="flex items-center gap-2 text-xs text-red-500">
                    <AlertCircle className="h-3 w-3" />
                    {error}
                </div>
            )}
        </div>
    );
}
