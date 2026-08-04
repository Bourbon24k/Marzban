import {
  Box,
  chakra,
  HStack,
  IconButton,
  Text,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import {
  ArrowLeftOnRectangleIcon,
  Bars3Icon,
  ChartPieIcon,
  ClipboardDocumentListIcon,
  Cog6ToothIcon,
  CurrencyDollarIcon,
  DocumentMinusIcon,
  LinkIcon,
  SquaresPlusIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";
import { DONATION_URL } from "constants/Project";
import useGetUser from "hooks/useGetUser";
import { FC, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";
import { dismissDonationNotice, shouldShowDonation } from "./Header";

const iconProps = { baseStyle: { w: 5, h: 5 } };

const UsersNavIcon = chakra(UsersIcon, iconProps);
const HostsIcon = chakra(LinkIcon, iconProps);
const NodesIcon = chakra(SquaresPlusIcon, iconProps);
const UsageIcon = chakra(ChartPieIcon, iconProps);
const ResetUsageIcon = chakra(DocumentMinusIcon, iconProps);
const SettingsIcon = chakra(Cog6ToothIcon, iconProps);
const AuditIcon = chakra(ClipboardDocumentListIcon, iconProps);
const DonationIcon = chakra(CurrencyDollarIcon, iconProps);
const LogoutIcon = chakra(ArrowLeftOnRectangleIcon, iconProps);
const BurgerIcon = chakra(Bars3Icon, { baseStyle: { w: 4, h: 4 } });

const COLLAPSED_KEY = "yuku-sidebar-collapsed";

export const SIDEBAR_WIDTH = { collapsed: "60px", expanded: "220px" };

type Item = {
  to: string;
  label: string;
  icon: FC;
  sudoOnly?: boolean;
  external?: boolean;
  dot?: boolean;
};

const NavRow: FC<{
  item: Item;
  collapsed: boolean;
  active: boolean;
  onClick?: () => void;
}> = ({ item, collapsed, active, onClick }) => {
  const Icon = item.icon;
  const row = (
    <HStack
      as="span"
      w="full"
      spacing="3"
      px="3"
      py="2"
      borderRadius="md"
      position="relative"
      justifyContent={collapsed ? "center" : "flex-start"}
      bg={active ? "primary.500" : "transparent"}
      color={active ? "white" : undefined}
      _hover={{ bg: active ? "primary.500" : "gray.100", _dark: { bg: active ? "primary.500" : "gray.700" } }}
    >
      <Icon />
      {!collapsed && (
        <Text fontSize="sm" noOfLines={1}>
          {item.label}
        </Text>
      )}
      {item.dot && (
        <Box
          bg="yellow.500"
          w="2"
          h="2"
          rounded="full"
          position="absolute"
          top="2"
          right={collapsed ? "2" : "3"}
        />
      )}
    </HStack>
  );

  const link = item.external ? (
    <Link to={item.to} target="_blank" onClick={onClick}>
      {row}
    </Link>
  ) : (
    <Link to={item.to} onClick={onClick}>
      {row}
    </Link>
  );

  return collapsed ? (
    <Tooltip label={item.label} placement="right" openDelay={300}>
      <Box w="full">{link}</Box>
    </Tooltip>
  ) : (
    <Box w="full">{link}</Box>
  );
};

export const Sidebar: FC = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const { userData, getUserIsSuccess, getUserIsPending } = useGetUser();
  const isSudo = !getUserIsPending && getUserIsSuccess && userData?.is_sudo;

  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(COLLAPSED_KEY) === "1"
  );
  const [showDonationDot, setShowDonationDot] = useState(shouldShowDonation());

  useEffect(() => {
    localStorage.setItem(COLLAPSED_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  const items: Item[] = [
    { to: "/", label: t("sidebar.users"), icon: UsersNavIcon },
    { to: "/hosts", label: t("header.hostSettings"), icon: HostsIcon, sudoOnly: true },
    { to: "/nodes", label: t("header.nodeSettings"), icon: NodesIcon, sudoOnly: true },
    { to: "/nodes-usage", label: t("header.nodesUsage"), icon: UsageIcon, sudoOnly: true },
    { to: "/reset-usage", label: t("resetAllUsage"), icon: ResetUsageIcon, sudoOnly: true },
    { to: "/core", label: t("header.coreSettings"), icon: SettingsIcon, sudoOnly: true },
    { to: "/yuku", label: "YUKU настройки", icon: SettingsIcon, sudoOnly: true },
    { to: "/groups", label: "Лимиты по группам", icon: UsageIcon, sudoOnly: true },
    { to: "/audit", label: "История действий", icon: AuditIcon, sudoOnly: true },
  ];

  const footerItems: Item[] = [
    {
      to: DONATION_URL,
      label: t("header.donation"),
      icon: DonationIcon,
      external: true,
      dot: showDonationDot,
    },
    { to: "/login", label: t("header.logout"), icon: LogoutIcon },
  ];

  return (
    <VStack
      as="nav"
      align="stretch"
      spacing="1"
      w={collapsed ? SIDEBAR_WIDTH.collapsed : SIDEBAR_WIDTH.expanded}
      flexShrink={0}
      h="100vh"
      position="sticky"
      top="0"
      py="4"
      px="2"
      borderRightWidth="1px"
      borderColor="light-border"
      _dark={{ borderColor: "gray.700" }}
      transition="width 0.15s ease"
      overflowY="auto"
    >
      <HStack justifyContent={collapsed ? "center" : "space-between"} px="1" pb="2">
        {!collapsed && (
          <Text fontWeight="semibold" fontSize="md" noOfLines={1}>
            Yuku
          </Text>
        )}
        <IconButton
          size="sm"
          variant="ghost"
          aria-label={collapsed ? t("sidebar.expand") : t("sidebar.collapse")}
          onClick={() => setCollapsed((value) => !value)}
        >
          <BurgerIcon />
        </IconButton>
      </HStack>

      {items
        .filter((item) => !item.sudoOnly || isSudo)
        .map((item) => (
          <NavRow
            key={item.to}
            item={item}
            collapsed={collapsed}
            active={location.pathname === item.to}
          />
        ))}

      <Box flex="1" />

      {footerItems.map((item) => (
        <NavRow
          key={item.to}
          item={item}
          collapsed={collapsed}
          active={location.pathname === item.to}
          onClick={
            item.dot
              ? () => {
                  dismissDonationNotice();
                  setShowDonationDot(false);
                }
              : undefined
          }
        />
      ))}
    </VStack>
  );
};
