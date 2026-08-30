import React from "react";
import { Navigate } from "react-router-dom";
import { useDemoAuth, type DemoRole } from "../../services/demoAuth";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: DemoRole;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const { user } = useDemoAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (requiredRole && user.role !== requiredRole) return <Navigate to="/dashboard/recovery" replace />;

  return <>{children}</>;
};

export default ProtectedRoute;
