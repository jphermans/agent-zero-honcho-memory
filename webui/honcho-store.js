import { createStore } from "/js/AlpineStore.js";
import { apiRequest } from "/js/api.js";
import { toastFrontendSuccess, toastFrontendError, toastFrontendWarning } from "/components/notifications/notification-store.js";

export const store = createStore("honchoSharedMemoryStore", {
    secretStatus: "Checking...",
    diagnostics: null,

    init() {
        this.checkSecretStatus();
    },

    onOpen() {
        this.checkSecretStatus();
    },

    cleanup() {},

    async checkSecretStatus() {
        try {
            const res = await apiRequest("GET", "/api/plugins/honcho_shared_memory/secret_status");
            if (res.ok) {
                const data = await res.json();
                this.secretStatus = data.configured ? "✅ Configured" : "❌ Missing";
            } else {
                this.secretStatus = "⚠️ Unknown";
            }
        } catch {
            this.secretStatus = "⚠️ Error checking";
        }
    },

    async testConnection() {
        toastFrontendWarning("Testing connection...", "Honcho");
        try {
            const res = await apiRequest("POST", "/api/plugins/honcho_shared_memory/test_connection");
            const data = await res.json();
            this.diagnostics = data;
            if (data.success) {
                toastFrontendSuccess(data.message || "Connection successful", "Honcho");
            } else {
                toastFrontendError(data.message || "Connection failed", "Honcho");
            }
        } catch (e) {
            toastFrontendError("Connection test error: " + e.message, "Honcho");
        }
    },

    viewDiagnostics() {
        if (this.diagnostics) {
            const diagText = JSON.stringify(this.diagnostics, null, 2);
            toastFrontendWarning("Diagnostics:\n" + diagText, "Honcho");
        } else {
            toastFrontendWarning("No diagnostics available. Run 'Test Connection' first.", "Honcho");
        }
    },

    resetDefaults() {
        // Reload default config by resetting to plugin defaults
        if (confirm("Reset all settings to defaults?")) {
            // This triggers the settings modal to reload defaults
            this.dispatch(new CustomEvent("honcho-reset"));
            toastFrontendWarning("Settings reset requested. Save to persist.", "Honcho");
        }
    },

    // Dispatch helper
    dispatch(event) {
        document.dispatchEvent(event);
    },
});
