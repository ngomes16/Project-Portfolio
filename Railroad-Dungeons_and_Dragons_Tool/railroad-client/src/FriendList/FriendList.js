import React, { useEffect, useState } from "react";
import Friend from "./Friend";
import { List, ListItem, ListItemButton, ListDivider, Stack } from "@mui/joy";
import styled from "styled-components";

const Wrapper = styled(Stack)`
  width: 300px;
  height: 400px;
  overflow: scroll;
`;

export default function FriendList() {
  const [userId, setUserId] = useState("0e62e9790a6141159313c8e9735276d1");
  const [friendList, setFriendList] = useState([]);

  useEffect(() => {
    fetch(`/api/friends/${userId}`)
      .then((res) => res.json())
      .then((data) => setFriendList(data));
  }, []);

  return (
    <Wrapper>
      Friends
      <List size="sm" variant="outlined">
        {friendList.map((f, idx) => (
          <div key={idx}>
            <ListItem>
              <ListItemButton>
                <Friend friend={f} />
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
    </Wrapper>
  );
}
