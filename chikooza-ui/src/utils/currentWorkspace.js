const CURRENT_WORKSPACE_KEY_PREFIX = "chikooza-current-workspace";
export const LEGACY_DAILY_SELECTOR_DRAFT_KEY = "chikooza-daily-selector-draft";

export const normalizeWorkspaceId = (value) => {
  if (value === undefined || value === null || value === "" || value === 0 || value === "0") {
    return "0";
  }
  return String(value);
};

export const isValidWorkspaceId = (value) => normalizeWorkspaceId(value) !== "0";

const safeParse = (value) => {
  try {
    return JSON.parse(value || "{}");
  } catch {
    return {};
  }
};

export const getCurrentWorkspaceKey = () => {
  const userId = localStorage.getItem("publicid") || localStorage.getItem("userid") || "anonymous";
  return `${CURRENT_WORKSPACE_KEY_PREFIX}-${userId}`;
};

export const readCurrentWorkspace = () => {
  const current = safeParse(localStorage.getItem(getCurrentWorkspaceKey()));
  return {
    farmPublicId: normalizeWorkspaceId(current.farmPublicId || current.selectedFarmId),
    flockPublicId: normalizeWorkspaceId(current.flockPublicId || current.selectedFlockId),
    updatedAt: Number(current.updatedAt || 0),
    source: current.source || "current_workspace",
  };
};

export const readLegacySelectorWorkspace = () => {
  const legacy = safeParse(localStorage.getItem(LEGACY_DAILY_SELECTOR_DRAFT_KEY));
  return {
    farmPublicId: normalizeWorkspaceId(legacy.selectedFarmId || legacy.farmPublicId),
    flockPublicId: normalizeWorkspaceId(legacy.selectedFlockId || legacy.flockPublicId),
    updatedAt: Number(legacy.updatedAt || 0),
    source: legacy.source || "legacy_daily_selector",
  };
};

export const readInitialWorkspace = () => {
  const current = readCurrentWorkspace();
  if (isValidWorkspaceId(current.farmPublicId) || isValidWorkspaceId(current.flockPublicId)) {
    return current;
  }
  return readLegacySelectorWorkspace();
};

export const writeLegacySelectorWorkspace = ({ farmPublicId, flockPublicId, source = "current_workspace" }) => {
  const previous = safeParse(localStorage.getItem(LEGACY_DAILY_SELECTOR_DRAFT_KEY));
  const farmId = normalizeWorkspaceId(farmPublicId !== undefined ? farmPublicId : previous.selectedFarmId);
  const flockId = normalizeWorkspaceId(flockPublicId !== undefined ? flockPublicId : previous.selectedFlockId);

  localStorage.setItem(LEGACY_DAILY_SELECTOR_DRAFT_KEY, JSON.stringify({
    ...previous,
    selectedFarmId: farmId,
    selectedFlockId: flockId,
    selectorStep: Number(previous.selectorStep || 0),
    updatedAt: Date.now(),
    source,
  }));
};

export const writeCurrentWorkspace = ({ farmPublicId, flockPublicId, source = "manual" }) => {
  const previous = readCurrentWorkspace();
  const farmId = normalizeWorkspaceId(farmPublicId !== undefined ? farmPublicId : previous.farmPublicId);
  const flockId = normalizeWorkspaceId(flockPublicId !== undefined ? flockPublicId : previous.flockPublicId);
  const payload = {
    farmPublicId: farmId,
    flockPublicId: flockId,
    updatedAt: Date.now(),
    source,
  };

  localStorage.setItem(getCurrentWorkspaceKey(), JSON.stringify(payload));
  writeLegacySelectorWorkspace({ farmPublicId: farmId, flockPublicId: flockId, source });
  return payload;
};

export const resolveWorkspaceFarm = (farms = [], preferredFarmId = "0") => {
  const validFarms = farms.filter((farm) => isValidWorkspaceId(farm?.public_id));
  if (validFarms.length === 0) {
    return null;
  }

  const preferredId = normalizeWorkspaceId(preferredFarmId);
  return validFarms.find((farm) => normalizeWorkspaceId(farm.public_id) === preferredId) || validFarms[validFarms.length - 1];
};

export const resolveWorkspaceFlock = (flocks = [], preferredFlockId = "0") => {
  const validFlocks = flocks.filter((flock) => isValidWorkspaceId(flock?.flock_public_id));
  if (validFlocks.length === 0) {
    return null;
  }

  const preferredId = normalizeWorkspaceId(preferredFlockId);
  return validFlocks.find((flock) => normalizeWorkspaceId(flock.flock_public_id) === preferredId) || validFlocks[validFlocks.length - 1];
};
