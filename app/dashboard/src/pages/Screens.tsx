/**
 * One page per item of what used to be the burger menu.
 *
 * The screens themselves are the existing components; <PageMode> strips their
 * dialog chrome (see components/PageOrModal). The ones that live in the
 * dashboard store are switched on while their route is mounted, so their data
 * still loads exactly as it did when a menu item opened them, and closing one
 * (Cancel, or a successful save) lands back on the users page.
 */
import { AuditLogModal } from "components/AuditLogModal";
import { CoreSettingsModal } from "components/CoreSettingsModal";
import { HostGroupsModal } from "components/HostGroupsModal";
import { HostsDialog } from "components/HostsDialog";
import { NodesDialog } from "components/NodesModal";
import { NodesUsage } from "components/NodesUsage";
import { PageMode } from "components/PageOrModal";
import { ResetAllUsageModal } from "components/ResetAllUsageModal";
import { YukuSettingsModal } from "components/YukuSettingsModal";
import { useDashboard } from "contexts/DashboardContext";
import { FC, PropsWithChildren, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

/** Keeps a store-driven screen open for the lifetime of its route. */
const useStoreScreen = (isOpen: boolean, setOpen: (open: boolean) => void) => {
  const navigate = useNavigate();
  const wasOpen = useRef(false);

  useEffect(() => {
    setOpen(true);
    return () => setOpen(false);
  }, []);

  useEffect(() => {
    if (isOpen) wasOpen.current = true;
    // closed from inside the screen (cancel/save) — leave the route with it,
    // but not on the first render, when it hasn't been opened yet
    else if (wasOpen.current) navigate("/");
  }, [isOpen]);
};

const Screen: FC<PropsWithChildren> = ({ children }) => (
  <PageMode>{children}</PageMode>
);

export const HostsPage: FC = () => {
  const { isEditingHosts, onEditingHosts } = useDashboard();
  useStoreScreen(isEditingHosts, onEditingHosts);
  return (
    <Screen>
      <HostsDialog />
    </Screen>
  );
};

export const NodesPage: FC = () => {
  const { isEditingNodes, onEditingNodes } = useDashboard();
  useStoreScreen(isEditingNodes, onEditingNodes);
  return (
    <Screen>
      <NodesDialog />
    </Screen>
  );
};

export const NodesUsagePage: FC = () => {
  const { isShowingNodesUsage, onShowingNodesUsage } = useDashboard();
  useStoreScreen(isShowingNodesUsage, onShowingNodesUsage);
  return (
    <Screen>
      <NodesUsage />
    </Screen>
  );
};

export const ResetUsagePage: FC = () => {
  const { isResetingAllUsage, onResetAllUsage } = useDashboard();
  useStoreScreen(isResetingAllUsage, onResetAllUsage);
  return (
    <Screen>
      <ResetAllUsageModal />
    </Screen>
  );
};

export const CoreSettingsPage: FC = () => {
  const isEditingCore = useDashboard((state) => state.isEditingCore);
  useStoreScreen(isEditingCore, (isEditingCore) =>
    useDashboard.setState({ isEditingCore })
  );
  return (
    <Screen>
      <CoreSettingsModal />
    </Screen>
  );
};

/** The prop-driven screens need nothing from the store. */
const propScreen = (
  Component: FC<{ isOpen: boolean; onClose: () => void }>
): FC => {
  const Page: FC = () => {
    const navigate = useNavigate();
    return (
      <Screen>
        <Component isOpen onClose={() => navigate("/")} />
      </Screen>
    );
  };
  return Page;
};

export const YukuSettingsPage = propScreen(YukuSettingsModal);
export const HostGroupsPage = propScreen(HostGroupsModal);
export const AuditLogPage = propScreen(AuditLogModal);
