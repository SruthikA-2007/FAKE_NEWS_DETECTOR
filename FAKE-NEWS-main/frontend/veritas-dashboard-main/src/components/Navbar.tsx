import { Shield } from "lucide-react";

const Navbar = () => {
  return (
    <nav className="glass sticky top-0 z-50 border-x-0 border-t-0 rounded-none px-6 py-4">
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold tracking-tight text-foreground">
            Veri<span className="text-gradient-red">Fact</span> AI
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          Model Online
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
