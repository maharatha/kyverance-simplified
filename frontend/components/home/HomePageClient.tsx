"use client";

import { useMemo, useState } from "react";
import {
  getHomeFixture,
  HOME_PAGE_STATES,
  type HomePageState,
} from "@/lib/home";
import { HomeShell } from "./HomeShell";
import "./home.css";

const DEFAULT_STATE: HomePageState = "signed-out";

function isHomePageState(value: string): value is HomePageState {
  return (HOME_PAGE_STATES as string[]).includes(value);
}

type HomePageClientProps = {
  /** Optional initial state for tests. Ignored in production builds. */
  initialState?: HomePageState;
};

export function HomePageClient({ initialState }: HomePageClientProps) {
  const isProduction = process.env.NODE_ENV === "production";
  const showDevSwitcher = process.env.NODE_ENV === "development";
  const [state, setState] = useState<HomePageState>(initialState ?? DEFAULT_STATE);
  const [menuOpen, setMenuOpen] = useState(false);

  const activeState = isProduction ? DEFAULT_STATE : state;
  const fixture = useMemo(() => getHomeFixture(activeState), [activeState]);

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
          </div>
        </div>
      ) : null}
      <HomeShell
        fixture={fixture}
        menuOpen={menuOpen}
        onMenuToggle={() => setMenuOpen((open) => !open)}
      />
    </>
  );
}
