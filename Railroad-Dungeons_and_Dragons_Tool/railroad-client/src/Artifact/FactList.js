import { List, ListItem } from "@mui/joy";
import React from "react";
import Fact from "./Fact";

export default function FactList({ list }) {
  if (!list) return null;
  return (
    <List>
      {list.map((fact, idx) => (
        <ListItem sx={{ display: "block" }} key={idx}>
          <Fact factId={fact.id} />
        </ListItem>
      ))}
    </List>
  );
}
