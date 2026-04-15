import { MatchedArticle } from "@/services/api";
import { ExternalLink, CheckCircle, AlertCircle, HelpCircle } from "lucide-react";

interface SourceVerificationProps {
  matched_articles: MatchedArticle[];
  verification_summary: string;
}

const SourceVerification = ({ matched_articles, verification_summary }: SourceVerificationProps) => {
  const supportingCount = matched_articles.filter((a) => a.verdict_alignment === "supporting").length;
  const contradictingCount = matched_articles.filter((a) => a.verdict_alignment === "contradicting").length;
  const neutralCount = matched_articles.filter((a) => a.verdict_alignment === "neutral").length;

  const getAlignmentIcon = (alignment: string) => {
    switch (alignment) {
      case "supporting":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "contradicting":
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <HelpCircle className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getAlignmentLabel = (alignment: string) => {
    switch (alignment) {
      case "supporting":
        return "Supporting";
      case "contradicting":
        return "Contradicting";
      default:
        return "Neutral";
    }
  };

  const getAlignmentColor = (alignment: string) => {
    switch (alignment) {
      case "supporting":
        return "bg-green-500/10 border-green-500/30";
      case "contradicting":
        return "bg-red-500/10 border-red-500/30";
      default:
        return "bg-yellow-500/10 border-yellow-500/30";
    }
  };

  return (
    <div className="space-y-6">
      {/* Summary Section */}
      <div className="glass border border-border/50 p-6 rounded-lg space-y-3">
        <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <span className="text-2xl">🔍</span>
          Verification Summary
        </h3>
        <p className="text-sm text-muted-foreground leading-relaxed">{verification_summary}</p>

        {/* Coverage Stats */}
        <div className="grid grid-cols-3 gap-3 pt-3 border-t border-border/30">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">{supportingCount}</div>
            <div className="text-xs text-muted-foreground">Supporting</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400">{contradictingCount}</div>
            <div className="text-xs text-muted-foreground">Contradicting</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">{neutralCount}</div>
            <div className="text-xs text-muted-foreground">Neutral</div>
          </div>
        </div>
      </div>

      {/* Matched Articles Section */}
      {matched_articles.length > 0 && (
        <div className="glass border border-border/50 p-6 rounded-lg space-y-4">
          <h3 className="text-lg font-semibold text-foreground">Found Sources ({matched_articles.length})</h3>

          <div className="space-y-3 max-h-96 overflow-y-auto">
            {matched_articles.map((article, idx) => (
              <div
                key={`${article.source}-${idx}`}
                className={`border rounded-lg p-4 transition-all hover:shadow-lg cursor-pointer ${getAlignmentColor(article.verdict_alignment)}`}
              >
                {/* Header with alignment badge */}
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2 flex-1">
                    {getAlignmentIcon(article.verdict_alignment)}
                    <span className="text-xs font-semibold text-foreground uppercase tracking-wider">
                      {getAlignmentLabel(article.verdict_alignment)}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Match: {(article.match_score * 100).toFixed(0)}%
                  </div>
                </div>

                {/* Title */}
                <h4 className="text-sm font-semibold text-foreground mb-2 line-clamp-2 hover:text-primary transition-colors">
                  {article.title}
                </h4>

                {/* Source and Meta */}
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-muted-foreground">{article.source}</span>
                  {article.description && (
                    <span className="text-xs text-muted-foreground italic max-w-xs truncate">
                      {article.description}
                    </span>
                  )}
                </div>

                {/* Link to source */}
                {article.url && (
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:text-primary/80 underline flex items-center gap-1 transition-colors"
                  >
                    Read full source
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {matched_articles.length === 0 && (
        <div className="glass border border-border/50 p-6 rounded-lg text-center text-muted-foreground">
          <HelpCircle className="h-12 w-12 opacity-30 mx-auto mb-3" />
          <p className="text-sm">No corroborating sources found in available databases.</p>
        </div>
      )}
    </div>
  );
};

export default SourceVerification;
