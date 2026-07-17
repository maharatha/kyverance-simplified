import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import MicrosoftEntraID from "next-auth/providers/microsoft-entra-id";
import {
  authConfig,
  entraProviderConfig,
  isEntraConfigured,
  isLocalDevIdentityEnabled,
} from "./auth.config";

const providers = [];

if (isEntraConfigured() && entraProviderConfig.issuer) {
  providers.push(
    MicrosoftEntraID({
      clientId: entraProviderConfig.clientId!,
      clientSecret: entraProviderConfig.clientSecret!,
      issuer: entraProviderConfig.issuer,
      authorization: entraProviderConfig.authorizeUrl
        ? {
            url: entraProviderConfig.authorizeUrl,
            params: {
              scope: `openid profile email offline_access ${entraProviderConfig.apiScope}`,
              ...(entraProviderConfig.userFlow ? { p: entraProviderConfig.userFlow } : {}),
            },
          }
        : {
            params: {
              scope: `openid profile email offline_access ${entraProviderConfig.apiScope}`,
            },
          },
      ...(entraProviderConfig.tokenUrl ? { token: entraProviderConfig.tokenUrl } : {}),
    }),
  );
}

if (isLocalDevIdentityEnabled()) {
  providers.push(
    Credentials({
      id: "development",
      name: "Local development",
      credentials: {
        confirm: { label: "Confirm", type: "text" },
      },
      async authorize() {
        if (!isLocalDevIdentityEnabled()) return null;
        return {
          id: "dev-user-001",
          name: "Dev User",
          email: "dev@kyverance.local",
          isDev: true,
        };
      },
    }),
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  providers,
});

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    idToken?: string;
    idp?: string;
    isDev?: boolean;
    error?: string;
  }

  interface User {
    isDev?: boolean;
  }
}

declare module "@auth/core/jwt" {
  interface JWT {
    accessToken?: string;
    idToken?: string;
    idp?: string;
    refreshToken?: string;
    expiresAt?: number;
    isDev?: boolean;
    error?: string;
  }
}
