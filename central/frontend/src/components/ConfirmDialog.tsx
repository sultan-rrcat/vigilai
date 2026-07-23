// src/components/ConfirmDialog.tsx
import { AlertTriangle } from 'lucide-react';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from './ui/dialog';

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'default' | 'destructive';
  onConfirm: () => void;
  isLoading?: boolean;
}

/**
 * Shared confirmation modal. Use this instead of window.confirm()
 * for any destructive or otherwise consequential action.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  onConfirm,
  isLoading = false,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-zinc-950 border border-zinc-800 text-zinc-100 sm:max-w-[400px]">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            {variant === 'destructive' && (
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-500/10">
                <AlertTriangle className="h-4 w-4 text-red-500" />
              </span>
            )}
            <DialogTitle className="text-sm font-medium text-zinc-100">{title}</DialogTitle>
          </div>
          <DialogDescription className="text-xs leading-relaxed text-zinc-500 pt-1">
            {description}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="pt-2 gap-2 sm:gap-2 bg-black">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
            className="h-8 text-xs text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={
              variant === 'destructive'
                ? 'h-8 px-4 text-xs bg-red-600 hover:bg-red-500 text-white'
                : 'h-8 px-4 text-xs bg-indigo-600 hover:bg-indigo-500 text-white'
            }
          >
            {isLoading ? 'Please wait…' : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
