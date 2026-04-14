import { useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import MeshBackground from "@/components/MeshBackground";
import Navbar from "@/components/Navbar";
import InputSwitcher from "@/components/InputSwitcher";
import PipelineLoader from "@/components/PipelineLoader";
import CredibilityGauge from "@/components/CredibilityGauge";
import BentoClaimCards from "@/components/BentoClaimCards";
import EntityHighlighter from "@/components/EntityHighlighter";
import { analyzeContent, type AnalyzeClaim, type AnalyzeInputType, type Entity } from "@/services/api";

type Phase = "input" | "loading" | "results";

type AnalyzePayload = {
  type: AnalyzeInputType;
  contentOrFile: string | File;
};

const Index = () => {
  const [phase, setPhase] = useState<Phase>("input");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overallScore, setOverallScore] = useState<number>(0);
  const [claimsData, setClaimsData] = useState<AnalyzeClaim[]>([]);
  const [articleText, setArticleText] = useState<string>("");
  const [entitiesData, setEntitiesData] = useState<Entity[]>([]);

  const handleAnalyze = useCallback(async (payload: AnalyzePayload) => {
    setError(null);
    setIsLoading(true);
    setPhase("loading");

    try {
      const response = await analyzeContent(payload.type, payload.contentOrFile);
      setOverallScore(response.overall_score);
      setClaimsData(response.claims);
      setArticleText(response.article_text);
      setEntitiesData(response.entities);
      setPhase("results");
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Analysis failed.";
      setError(message);
      setPhase("input");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleReset = useCallback(() => {
    setPhase("input");
    setError(null);
    setIsLoading(false);
    setOverallScore(0);
    setClaimsData([]);
    setArticleText("");
    setEntitiesData([]);
  }, []);

  return (
    <div className="min-h-screen">
      <MeshBackground />
      <Navbar />

      <main className="container mx-auto max-w-4xl px-4 py-10 space-y-8">
        <AnimatePresence mode="wait">
          {phase === "input" && (
            <motion.div
              key="input"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="space-y-6"
            >
              <div className="text-center space-y-2">
                <h1 className="text-3xl font-bold tracking-tight text-foreground">
                  Fake News <span className="text-gradient-red">Detector</span>
                </h1>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  AI-powered credibility analysis in real time
                </p>
              </div>
              <InputSwitcher onAnalyze={handleAnalyze} />
              {error && (
                <div className="glass border border-red-500/25 px-4 py-3 text-sm text-red-300">
                  {error}
                </div>
              )}
            </motion.div>
          )}

          {phase === "loading" && (
            <motion.div
              key="loading"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              {isLoading ? <PipelineLoader /> : null}
            </motion.div>
          )}

          {phase === "results" && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="space-y-6"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold tracking-tight text-foreground">Analysis Results</h2>
                <button
                  onClick={handleReset}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 rounded-md border border-border hover:border-primary/40"
                >
                  New Analysis
                </button>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <CredibilityGauge score={overallScore} />
                <EntityHighlighter text={articleText} entities={entitiesData} />
              </div>
              <BentoClaimCards claims={claimsData} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

export default Index;
