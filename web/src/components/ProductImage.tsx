import { useState } from "react";

/** Image locale affichée quand un produit n'a pas d'image ou que l'image ne se charge pas. */
export const PLACEHOLDER_IMAGE = "/produit-sans-image.svg";

export function ProductImage({
  src,
  alt,
  width,
  height,
  lazy = false,
}: {
  src: string | null | undefined;
  alt: string;
  width: number;
  height: number;
  lazy?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const usePlaceholder = !src || failed;
  return (
    <img
      src={usePlaceholder ? PLACEHOLDER_IMAGE : src}
      alt={usePlaceholder ? "" : alt}
      data-placeholder={usePlaceholder ? "true" : undefined}
      loading={lazy ? "lazy" : undefined}
      width={width}
      height={height}
      onError={() => setFailed(true)}
    />
  );
}
