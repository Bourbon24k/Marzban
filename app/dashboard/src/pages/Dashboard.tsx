import { Box } from "@chakra-ui/react";
import { DeleteUserModal } from "components/DeleteUserModal";
import { DeviceStats } from "components/DeviceStats";
import { Filters } from "components/Filters";
import { QRCodeDialog } from "components/QRCodeDialog";
import { ResetUserUsageModal } from "components/ResetUserUsageModal";
import { RevokeSubscriptionModal } from "components/RevokeSubscriptionModal";
import { UserDialog } from "components/UserDialog";
import { UsersTable } from "components/UsersTable";
import { fetchInbounds, useDashboard } from "contexts/DashboardContext";
import { FC, useEffect } from "react";
import { Statistics } from "../components/Statistics";

/** The users screen. Everything that used to sit behind the burger menu has a
 *  route of its own now (pages/Screens.tsx); the sidebar, header and footer
 *  live in components/Layout and wrap every page. */
export const Dashboard: FC = () => {
  useEffect(() => {
    useDashboard.getState().refetchUsers();
    fetchInbounds();
  }, []);
  return (
    <Box w="full">
      <Statistics />
      <DeviceStats mt="4" />
      <Filters />
      <UsersTable />
      <UserDialog />
      <DeleteUserModal />
      <QRCodeDialog />
      <ResetUserUsageModal />
      <RevokeSubscriptionModal />
    </Box>
  );
};

export default Dashboard;
