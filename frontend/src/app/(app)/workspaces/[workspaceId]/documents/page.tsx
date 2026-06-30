"use client";

import { use, useRef, useState, useCallback } from "react";
import { FileText, RefreshCw, Trash2, Upload, UploadCloud } from "lucide-react";

import {
  useDocuments,
  useUploadDocument,
  useDeleteDocument,
  useRequeueDocument,
} from "@/hooks/useDocuments";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { Document, DocumentStatus } from "@/types";

const STATUS_VARIANT: Record<
  DocumentStatus,
  "default" | "secondary" | "success" | "warning" | "destructive"
> = {
  pending: "secondary",
  processing: "warning",
  ready: "success",
  failed: "destructive",
};

const STATUS_LABEL: Record<DocumentStatus, string> = {
  pending: "Ausstehend",
  processing: "Verarbeitung…",
  ready: "Bereit",
  failed: "Fehler",
};

const ACCEPTED_MIME = new Set([
  "text/plain",
  "text/markdown",
  "text/csv",
  "text/html",
  "application/pdf",
  "application/json",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
]);
const ACCEPTED_EXT = [".txt", ".md", ".csv", ".html", ".json", ".pdf", ".xlsx", ".xls"];

function isAccepted(file: File): boolean {
  if (ACCEPTED_MIME.has(file.type)) return true;
  return ACCEPTED_EXT.some((ext) => file.name.toLowerCase().endsWith(ext));
}

interface UploadJob {
  id: string;
  name: string;
  status: "uploading" | "done" | "error";
  error?: string;
}

export default function DocumentsPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = use(params);
  const { data: documents, isLoading } = useDocuments(workspaceId);
  const upload = useUploadDocument(workspaceId);
  const deleteDoc = useDeleteDocument(workspaceId);
  const requeue = useRequeueDocument(workspaceId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragCounter = useRef(0);
  const [uploadJobs, setUploadJobs] = useState<UploadJob[]>([]);

  function startUploads(files: File[]) {
    const accepted = files.filter(isAccepted);
    accepted.forEach((file) => {
      const id = crypto.randomUUID();
      setUploadJobs((prev) => [...prev, { id, name: file.name, status: "uploading" }]);
      void upload
        .mutateAsync(file)
        .then(() => {
          setUploadJobs((prev) => prev.map((j) => (j.id === id ? { ...j, status: "done" } : j)));
          setTimeout(() => setUploadJobs((prev) => prev.filter((j) => j.id !== id)), 3000);
        })
        .catch((err: unknown) => {
          setUploadJobs((prev) =>
            prev.map((j) =>
              j.id === id
                ? {
                    ...j,
                    status: "error" as const,
                    error: err instanceof Error ? err.message : "Upload fehlgeschlagen",
                  }
                : j,
            ),
          );
        });
    });
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files) return;
    startUploads(Array.from(e.target.files));
    e.target.value = "";
  }

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (Array.from(e.dataTransfer.types).includes("Files")) setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter.current = 0;
      setIsDragging(false);
      startUploads(Array.from(e.dataTransfer.files));
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [upload],
  );

  const activeJobs = uploadJobs.filter((j) => j.status !== "done");

  return (
    <div
      className="flex flex-1 flex-col overflow-hidden"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="pointer-events-none absolute inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-primary px-16 py-12 text-center">
            <UploadCloud className="h-12 w-12 text-primary" />
            <p className="text-lg font-semibold text-primary">Dateien hier ablegen</p>
            <p className="text-sm text-muted-foreground">PDF, TXT, MD, CSV, HTML, JSON</p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h2 className="font-semibold">Dokumente</h2>
          <p className="text-xs text-muted-foreground">
            Dateien hochladen oder hierher ziehen — max. 10 MB pro Datei.
          </p>
        </div>
        <Button onClick={() => fileInputRef.current?.click()}>
          <Upload className="h-4 w-4" />
          Hochladen
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.csv,.html,.json,.pdf,.xlsx,.xls"
          multiple
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {/* Upload progress queue */}
        {activeJobs.length > 0 && (
          <div className="mb-4 space-y-2">
            {activeJobs.map((job) => (
              <div
                key={job.id}
                className={`flex items-center gap-3 rounded-md px-4 py-2 text-sm ${
                  job.status === "error"
                    ? "bg-destructive/10 text-destructive"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {job.status === "uploading" && (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin shrink-0" />
                )}
                <span className="truncate flex-1">{job.name}</span>
                {job.status === "error" && <span className="text-xs">{job.error}</span>}
              </div>
            ))}
          </div>
        )}

        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-14 rounded-lg" />
            ))}
          </div>
        )}

        {!isLoading && (!documents || documents.length === 0) && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-20 text-center">
            <UploadCloud className="mb-3 h-12 w-12 text-muted-foreground" />
            <p className="font-medium">Noch keine Dokumente</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Dateien hochladen oder hierher ziehen.
            </p>
          </div>
        )}

        {!isLoading && documents && documents.length > 0 && (
          <div className="space-y-2">
            {documents.map((doc) => (
              <DocumentRow
                key={doc.id}
                document={doc}
                onDelete={() => void deleteDoc.mutateAsync(doc.id)}
                onRequeue={() => void requeue.mutateAsync(doc.id)}
                deleting={deleteDoc.isPending}
                requeuing={requeue.isPending}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DocumentRow({
  document: doc,
  onDelete,
  onRequeue,
  deleting,
  requeuing,
}: {
  document: Document;
  onDelete: () => void;
  onRequeue: () => void;
  deleting: boolean;
  requeuing: boolean;
}) {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-border bg-card px-4 py-3">
      <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium">{doc.name}</p>
        <p className="text-xs text-muted-foreground">{doc.mime_type}</p>
      </div>
      <Badge variant={STATUS_VARIANT[doc.status]}>{STATUS_LABEL[doc.status]}</Badge>
      {doc.status === "failed" && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-primary"
          onClick={onRequeue}
          disabled={requeuing}
          title="Erneut verarbeiten"
        >
          <RefreshCw className={`h-4 w-4 ${requeuing ? "animate-spin" : ""}`} />
        </Button>
      )}
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-muted-foreground hover:text-destructive"
        onClick={onDelete}
        disabled={deleting}
        aria-label="Dokument löschen"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}
