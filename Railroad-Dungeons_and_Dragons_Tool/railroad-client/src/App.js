import React, { useState } from "react";
import Sidebar from "./Sidebar/Sidebar";
import Artifact from "./Artifact/Artifact";
import FriendList from "./FriendList/FriendList";
import styled from "styled-components";
import { Stack } from "@mui/joy";

const Wrapper = styled(Stack)`
  padding: 10px;
`;

export default function App() {
  return (
    <Wrapper direction="row" justifyContent="space-between">
      <Sidebar />
      <Artifact />
      <FriendList />
    </Wrapper>
  );
}
