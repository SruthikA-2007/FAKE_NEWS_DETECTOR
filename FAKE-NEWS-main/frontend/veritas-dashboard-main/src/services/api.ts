import axios, { AxiosError } from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 60000,
});

export type AnalyzeInputType = "text" | "url" | "image";

export interface AnalyzeClaim {
  text: string;
  verdict: string;
  confidence: number;
  sources: string[];
}

export interface Entity {
  text: string;
  type: "person" | "date" | "money" | "org";
}

export interface AnalyzeResponse {
  claims: AnalyzeClaim[];
  overall_score: number;
  article_text: string;
  entities: Entity[];
}

const getFriendlyErrorMessage = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;

    if (!axiosError.response) {
      return "Unable to reach the verification service. Check that the backend is running and CORS is enabled.";
    }

    const backendDetail = axiosError.response.data?.detail;
    if (typeof backendDetail === "string" && backendDetail.trim()) {
      return backendDetail;
    }

    if (axiosError.response.status >= 500) {
      return "The backend returned an unexpected error while analyzing the content.";
    }

    return `Request failed with status ${axiosError.response.status}.`;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "An unexpected error occurred while analyzing the content.";
};

export const analyzeContent = async (type: AnalyzeInputType, contentOrFile: string | File) => {
  try {
    if (type === "image") {
      const formData = new FormData();
      formData.append("type", type);
      formData.append("file", contentOrFile);

      const response = await api.post<AnalyzeResponse>("/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      return response.data;
    }

    const response = await api.post<AnalyzeResponse>("/analyze", {
      type,
      content: contentOrFile,
    });

    return response.data;
  } catch (error) {
    throw new Error(getFriendlyErrorMessage(error));
  }
};

export default api;