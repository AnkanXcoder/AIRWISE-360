import { useCallback, useEffect, useRef, useState } from "react";
import { getIndiaStationMeasurements } from "../services/airwiseApi";

const REFRESH_INTERVAL = 5 * 60 * 1000;

export default function useStationData(source, sourceLocationId) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Every request receives an increasing ID. Responses from a previously
  // selected station are ignored if the user has since selected another one.
  const requestSequence = useRef(0);
  const hasLoadedRef = useRef(false);

  const fetchData = useCallback(async () => {
    const hasValidSelection =
      source &&
      sourceLocationId !== null &&
      sourceLocationId !== undefined &&
      String(sourceLocationId).trim() !== "";

    if (!hasValidSelection) {
      requestSequence.current += 1;
      hasLoadedRef.current = false;
      setData(null);
      setLoading(false);
      setRefreshing(false);
      setError(null);
      setLastUpdated(null);
      return;
    }

    const requestId = ++requestSequence.current;
    const isRefresh = hasLoadedRef.current;

    setLoading(!isRefresh);
    setRefreshing(isRefresh);
    setError(null);

    try {
      const result = await getIndiaStationMeasurements(
        source,
        sourceLocationId
      );

      if (requestId !== requestSequence.current) return;

      setData(result);
      setLastUpdated(result?.retrieved_at || null);
      hasLoadedRef.current = true;
    } catch (err) {
      if (requestId !== requestSequence.current) return;

      setError(
        err.response?.data?.detail ||
        err.message ||
        "Failed to fetch station measurements."
      );
    } finally {
      if (requestId === requestSequence.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [source, sourceLocationId]);

  useEffect(() => {
    // Invalidate any response belonging to the previous station.
    requestSequence.current += 1;
    hasLoadedRef.current = false;
    setData(null);
    setError(null);
    setLastUpdated(null);

    const hasValidSelection =
      source &&
      sourceLocationId !== null &&
      sourceLocationId !== undefined &&
      String(sourceLocationId).trim() !== "";

    if (!hasValidSelection) {
      setLoading(false);
      setRefreshing(false);
      return undefined;
    }

    let active = true;

    const load = () => {
      if (active) fetchData();
    };

    load();
    const intervalId = window.setInterval(load, REFRESH_INTERVAL);

    return () => {
      active = false;
      window.clearInterval(intervalId);
      // Any in-flight response from this effect becomes obsolete.
      requestSequence.current += 1;
    };
  }, [fetchData, source, sourceLocationId]);

  return {
    data,
    loading,
    refreshing,
    error,
    lastUpdated,
    refresh: fetchData
  };
}
