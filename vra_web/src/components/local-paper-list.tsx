import { LocalPaper } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { FileText, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface LocalPaperListProps {
    papers: LocalPaper[];
    onToggle: (id: string, checked: boolean) => void;
    onRemove: (id: string) => void;
}

export function LocalPaperList({
    papers,
    onToggle,
    onRemove,
}: LocalPaperListProps) {
    if (papers.length === 0) return null;

    return (
        <div className="space-y-2 mt-2 border rounded-md p-2 bg-muted/20">
            <h4 className="text-sm font-medium mb-2">Attached Documents</h4>
            <div className="space-y-1">
                {papers.map((paper) => (
                    <div
                        key={paper.canonical_id}
                        className="flex items-center justify-between p-2 rounded-md hover:bg-muted/50 text-sm group"
                    >
                        <div className="flex items-center gap-2 min-w-0">
                            <Checkbox
                                id={`paper-${paper.paper_id}`}
                                checked={paper.included}
                                onCheckedChange={(checked) =>
                                    onToggle(
                                        paper.canonical_id,
                                        checked as boolean
                                    )
                                }
                            />
                            <div className="truncate flex items-center gap-2">
                                <FileText className="h-3 w-3 text-muted-foreground" />
                                <span
                                    className="truncate max-w-[200px]"
                                    title={paper.title}
                                >
                                    {paper.title}
                                </span>
                            </div>
                            <Badge
                                variant="secondary"
                                className="text-[10px] px-1 h-5"
                            >
                                Local
                            </Badge>
                        </div>

                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                            onClick={() => onRemove(paper.canonical_id)}
                        >
                            <Trash2 className="h-3 w-3" />
                        </Button>
                    </div>
                ))}
            </div>
        </div>
    );
}
