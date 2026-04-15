import { useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import MeshBackground from "@/components/MeshBackground";
import Navbar from "@/components/Navbar";
import InputSwitcher from "@/components/InputSwitcher";
import PipelineLoader from "@/components/PipelineLoader";
import CredibilityGauge from "@/components/CredibilityGauge";
import BentoClaimCards from "@/components/BentoClaimCards";
import EntityHighlighter from "@/components/EntityHighlighter";
import SourceVerification from "@/components/SourceVerification";
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
  const [verificationSummary, setVerificationSummary] = useState<string>("");
  const [matchedArticles, setMatchedArticles] = useState<any[]>([]);
  const [credibilityLevel, setCredibilityLevel] = useState<string>("unverified");

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
      setVerificationSummary(response.verification_summary);
      setMatchedArticles(response.matched_articles);
      setCredibilityLevel(response.credibility_level);
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
    setVerificationSummary("");
    setMatchedArticles([]);
    setCredibilityLevel("unverified");
  }, []);

  return (
    <div className="min-h-screen">
      <MeshBackground />
      <Navbar />

      <main className="container mx-auto max-w-5xl px-4 py-10 space-y-8">
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
                  AI-powered credibility analysis with corroborating source verification
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

              {/* Credibility Score and Gauge */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <CredibilityGauge score={overallScore} />
                </div>
                <div className="glass border border-border/50 p-6 rounded-lg space-y-3">
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                    Credibility Level
                  </h3>
                  <div className="text-2xl font-bold text-foreground capitalize">
                    {credibilityLevel.replace(/_/g, " ")}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Based on corroborating sources from trusted news outlets and fact-checkers
                  </p>
                </div>
              </div>

              {/* Entity Highlighting */}
              {entitiesData.length > 0 && (
                <EntityHighlighter text={articleText} entities={entitiesData} />
              )}

              {/* Source Verification and Matched Articles */}
              <SourceVerification
                matched_articles={matchedArticles}
                verification_summary={verificationSummary}
              />

              {/* Claims Detail (if any) */}
              {claimsData.length > 0 && (
                <BentoClaimCards claims={claimsData} />
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

export default Index;
