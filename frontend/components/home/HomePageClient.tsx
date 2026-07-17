"use client";

import Link from "next/link";
import { signOut, useSession } from "next-auth/react";
import { useMemo, useState } from "react";
import {
  getHomeFixture,
  HOME_PAGE_STATES,
  type HomePageState,
} from "@/lib/home";
import { isSessionAuthenticated } from "@/lib/auth-session";
import { HomeShell } from "./HomeShell";
import "./home.css";

const DEFAULT_STATE: HomePageState = "signed-out";

function isHomePageState(value: string): value is HomePageState {
  return (HOME_PAGE_STATES as string[]).includes(value);
}

type HomePageClientProps = {
  /** Optional initial state for tests. Ignored in production builds. */
  initialState?: HomePageState;
  /** Optional session signed-in override for tests. */
  sessionSignedIn?: boolean;
};

export function HomePageClient({ initialState, sessionSignedIn }: HomePageClientProps) {
  const isProduction = process.env.NODE_ENV === "production";
  const showDevSwitcher = process.env.NODE_ENV === "development";
  const [state, setState] = useState<HomePageState>(initialState ?? DEFAULT_STATE);
  const [menuOpen, setMenuOpen] = useState(false);
  const { data: session, status } = useSession();

  const activeState = isProduction ? DEFAULT_STATE : state;
  const fixture = useMemo(() => getHomeFixture(activeState), [activeState]);
  const signedIn =
    sessionSignedIn ??
    (status === "authenticated" && isSessionAuthenticated(session));

  return (
    <>
      {showDevSwitcher ? (
        <div className="home-dev-switcher">
          <div className="home-dev-switcher-inner">
            <label htmlFor="home-dev-state">Dev home state</label>
            <select
              id="home-dev-state"
              value={activeState}
              onChange={(event) => {
                const next = event.target.value;
                if (isHomePageState(next)) {
                  setState(next);
                }
              }}
            >
              {HOME_PAGE_STATES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <Link href="/delivery-status" className="home-dev-delivery-link">
              Delivery board
            </Link>
          </div>
        </div>
      ) : null}
      <HomeShell
        fixture={fixture}
        sessionSignedIn={signedIn}
        menuOpen={menuOpen}
        onMenuToggle={() => setMenuOpen((open) => !open)}
        onSignOut={() => {
          void signOut({ callbackUrl: "/" });
        }}
      />
    </>
  );
}
