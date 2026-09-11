import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useUploadAvatar } from "../../hooks/useAccount";
import Avatar from "../Avatar";

export default function AvatarUploadDialog({ name, onOpenChange }: { name: string; onOpenChange: (open: boolean) => void }) {
  const upload = useUploadAvatar();
  const [preview, setPreview] = useState<string | null>(null);

  function handleFile(file: File | undefined) {
    if (!file) return;
    const image = new Image();
    const objectUrl = URL.createObjectURL(file);
    image.onload = () => {
      const size = Math.min(image.naturalWidth, image.naturalHeight);
      const canvas = document.createElement("canvas");
      canvas.width = 256;
      canvas.height = 256;
      const context = canvas.getContext("2d");
      if (!context) {
        URL.revokeObjectURL(objectUrl);
        return;
      }
      context.drawImage(image, (image.naturalWidth - size) / 2, (image.naturalHeight - size) / 2, size, size, 0, 0, 256, 256);
      setPreview(canvas.toDataURL("image/webp", 0.85));
      URL.revokeObjectURL(objectUrl);
    };
    image.onerror = () => URL.revokeObjectURL(objectUrl);
    image.src = objectUrl;
  }

  return (
    <Dialog.Root open onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-lg">
          <Dialog.Title className="text-base font-semibold text-stone-900">Change photo</Dialog.Title>
          <div className="mt-4 flex justify-center">
            {preview ? <img src={preview} alt="Photo preview" className="h-32 w-32 rounded-full object-cover" /> : <Avatar src={null} name={name} size="xl" />}
          </div>
          <input className="mt-4 block w-full text-sm" type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => handleFile(event.target.files?.[0])} />
          <div className="mt-5 flex justify-end gap-2">
            <button type="button" onClick={() => onOpenChange(false)} className="rounded border border-stone-300 px-3 py-1.5 text-sm">Cancel</button>
            <button type="button" onClick={() => preview && upload.mutate(preview, { onSuccess: () => onOpenChange(false) })} disabled={!preview || upload.isPending} className="rounded bg-stone-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50">{upload.isPending ? "Uploading…" : "Use photo"}</button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
