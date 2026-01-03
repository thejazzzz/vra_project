"use client";

import { useState, createContext, useContext, useCallback } from "react";
import { X } from "lucide-react";

interface Toast {
    id: string;
    title?: string;
    description: string;
    variant?: "default" | "destructive" | "success";
}

interface ToastContextType {
    toast: (props: Omit<Toast, "id">) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const toast = useCallback(
        ({ title, description, variant = "default" }: Omit<Toast, "id">) => {
            const id = Math.random().toString(36).substring(2, 9);
            setToasts((prev) => [...prev, { id, title, description, variant }]);

            // Auto dismiss
            setTimeout(() => {
                setToasts((prev) => prev.filter((t) => t.id !== id));
            }, 5000);
        },
        []
    );

    const removeToast = (id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    };

    return (
        <ToastContext.Provider value={{ toast }}>
            {children}
            <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
                {toasts.map((t) => {
                    let variantClasses =
                        "bg-white border-gray-200 text-gray-900";
                    if (t.variant === "destructive") {
                        variantClasses =
                            "bg-red-50 border-red-200 text-red-900";
                    } else if (t.variant === "success") {
                        variantClasses =
                            "bg-green-50 border-green-200 text-green-900";
                    }

                    return (
                        <div
                            key={t.id}
                            className={`p-4 rounded-lg shadow-lg border flex justify-between items-start gap-3 animate-in slide-in-from-right-full ${variantClasses}`}
                        >
                            <div className="flex-1">
                                {t.title && (
                                    <h5 className="font-semibold text-sm mb-1">
                                        {t.title}
                                    </h5>
                                )}
                                <p className="text-sm opacity-90">
                                    {t.description}
                                </p>
                            </div>
                            <button
                                onClick={() => removeToast(t.id)}
                                className="text-gray-400 hover:text-gray-600"
                                aria-label="Dismiss notification"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    );
                })}
            </div>
        </ToastContext.Provider>
    );
}

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error("useToast must be used within a ToastProvider");
    }
    return context;
};
