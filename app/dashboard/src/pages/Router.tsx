import { createHashRouter } from "react-router-dom";
import { Layout } from "../components/Layout";
import { RouteError } from "../components/RouteError";
import { fetch } from "../service/http";
import { getAuthToken } from "../utils/authStorage";
import { Dashboard } from "./Dashboard";
import { Login } from "./Login";
import {
    AuditLogPage,
    CoreSettingsPage,
    HostGroupsPage,
    HostsPage,
    NodesPage,
    NodesUsagePage,
    ResetUsagePage,
    YukuSettingsPage,
} from "./Screens";
const fetchAdminLoader = () => {
    return fetch("/admin", {
        headers: {
            Authorization: `Bearer ${getAuthToken()}`,
        },
    });
};
// Every screen the sidebar links to is a child of the layout route, so they
// share one admin check and one set of chrome.
export const router = createHashRouter([
    {
        path: "/",
        element: <Layout />,
        errorElement: <RouteError />,
        loader: fetchAdminLoader,
        children: [
            { index: true, element: <Dashboard /> },
            { path: "hosts", element: <HostsPage /> },
            { path: "nodes", element: <NodesPage /> },
            { path: "nodes-usage", element: <NodesUsagePage /> },
            { path: "reset-usage", element: <ResetUsagePage /> },
            { path: "core", element: <CoreSettingsPage /> },
            { path: "yuku", element: <YukuSettingsPage /> },
            { path: "groups", element: <HostGroupsPage /> },
            { path: "audit", element: <AuditLogPage /> },
        ],
    },
    {
        path: "/login/",
        element: <Login />,
    },
]);
