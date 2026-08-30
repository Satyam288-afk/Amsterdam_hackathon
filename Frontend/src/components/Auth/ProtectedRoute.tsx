import React from "react";
import { Navigate } from "react-router-dom";
import { useDemoAuth, type DemoRole } from "../../services/demoAuth";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: DemoRole;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const { user, loading } = useDemoAuth();
  if (loading) return <div className="min-h-screen bg-[#fefae0] flex items-center justify-center text-sm font-semibold text-[#3d2b1f]">Restoring secure session…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (requiredRole && user.role !== requiredRole) return <Navigate to="/dashboard/recovery" replace />;

  return <>{children}</>;
};

export default ProtectedRoute;
