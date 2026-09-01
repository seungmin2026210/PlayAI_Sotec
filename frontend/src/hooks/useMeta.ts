import { useEffect, useState } from "react";
import { fetchMeta } from "../api/meta";
import type { Meta } from "../types";

let cache: Meta | null = null;

export function useMeta(): Meta | null {
  const [meta, setMeta] = useState<Meta | null>(cache);
  useEffect(() => {
    if (cache) return;
    let alive = true;
    fetchMeta()
      .then((m) => {
        cache = m;
        if (alive) setMeta(m);
      })
      .catch(() => {
        /* 상위에서 처리 */
      });
    return () => {
      alive = false;
    };
  }, []);
  return meta;
}
