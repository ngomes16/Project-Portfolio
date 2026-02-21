import React from "react";
import ArtifactEntry from "./ArtifactEntry";
import {
  List as BaseList,
  ListItem,
  ListItemButton,
  ListDivider,
} from "@mui/joy";
import styled from "styled-components";

const List = styled(BaseList)`
  width: 100%;
  overflow: scroll;
  flex-grow: 0;
`;

export default function ArtifactList({ list }) {
  return (
    <List size="sm" variant="outlined">
      {list.map((art, idx) => (
        <div key={idx}>
          <ListItem>
            <ListItemButton>
              {/* <ListItemDecorator><Home /></ListItemDecorator> */}
              <ArtifactEntry artifact={art} />
              {/* <KeyboardArrowRight /> */}
            </ListItemButton>
          </ListItem>
          <ListDivider
            inset="gutter"
            sx={{
              background: "black",
            }}
          />
        </div>
      ))}
    </List>
  );
}
